// A dependency-free gRPC wire fixture, not a Spark Connect implementation.
// Go's net/http owns HTTP/2 framing, HPACK and flow control. RPCs use an empty
// protobuf request and stream protobuf messages: uint32 sequence = 1;
// bytes payload = 2. The client checks framing, ordering, EOF and trailers.
package main

import (
	"bufio"
	"bytes"
	"crypto/rand"
	"crypto/rsa"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/binary"
	"encoding/json"
	"encoding/pem"
	"errors"
	"fmt"
	"io"
	"log"
	"math/big"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"syscall"
	"time"
)

func must(err error) {
	if err != nil {
		log.Fatal(err)
	}
}
func require(ok bool, message string) {
	if !ok {
		log.Fatal(message)
	}
}
func write(path string, value []byte, mode os.FileMode) {
	must(os.MkdirAll(filepath.Dir(path), 0755))
	must(os.WriteFile(path, value, mode))
}
func serial() *big.Int {
	n, e := rand.Int(rand.Reader, new(big.Int).Lsh(big.NewInt(1), 128))
	must(e)
	return n
}
func pki(dir string) {
	now := time.Now()
	key, e := rsa.GenerateKey(rand.Reader, 2048)
	must(e)
	ca := &x509.Certificate{SerialNumber: serial(), Subject: pkix.Name{CommonName: "rehearsal CA"}, NotBefore: now.Add(-time.Hour), NotAfter: now.Add(24 * time.Hour), IsCA: true, BasicConstraintsValid: true, KeyUsage: x509.KeyUsageCertSign}
	der, e := x509.CreateCertificate(rand.Reader, ca, ca, &key.PublicKey, key)
	must(e)
	write(filepath.Join(dir, "public/ca.crt"), pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: der}), 0644)
	otherKey, e := rsa.GenerateKey(rand.Reader, 2048)
	must(e)
	other := *ca
	other.SerialNumber = serial()
	other.Subject.CommonName = "unrelated CA"
	der, e = x509.CreateCertificate(rand.Reader, &other, &other, &otherKey.PublicKey, otherKey)
	must(e)
	write(filepath.Join(dir, "public/wrong-ca.crt"), pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: der}), 0644)
	for _, host := range []string{"catalog", "sail"} {
		for _, kind := range []string{"valid", "expired", "wrong-san", "wrong-issuer"} {
			leafKey, e := rsa.GenerateKey(rand.Reader, 2048)
			must(e)
			leaf := &x509.Certificate{SerialNumber: serial(), Subject: pkix.Name{CommonName: host}, DNSNames: []string{host}, NotBefore: now.Add(-5 * time.Minute), NotAfter: now.Add(6 * time.Hour), BasicConstraintsValid: true, KeyUsage: x509.KeyUsageDigitalSignature | x509.KeyUsageKeyEncipherment, ExtKeyUsage: []x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth}}
			if kind == "expired" {
				leaf.NotBefore = now.Add(-2 * time.Hour)
				leaf.NotAfter = now.Add(-time.Hour)
			}
			if kind == "wrong-san" {
				leaf.DNSNames = []string{"other.test"}
			} // correct CN must not rescue wrong SAN
			issuer, signer := ca, key
			if kind == "wrong-issuer" {
				issuer, signer = &other, otherKey
			}
			der, e = x509.CreateCertificate(rand.Reader, leaf, issuer, &leafKey.PublicKey, signer)
			must(e)
			dest := filepath.Join(dir, host, kind)
			write(filepath.Join(dest, "server.crt"), pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: der}), 0644)
			write(filepath.Join(dest, "server.key"), pem.EncodeToMemory(&pem.Block{Type: "RSA PRIVATE KEY", Bytes: x509.MarshalPKCS1PrivateKey(leafKey)}), 0640)
		}
	}
	// CA signing keys remain in memory only; no signing key enters a mount.
}

func message(i int) []byte {
	// Protobuf field 1 (varint), then field 2 (bytes). Payload exceeds one HTTP/2 frame.
	b := binary.AppendUvarint([]byte{8}, uint64(i))
	b = append(b, 18)
	b = binary.AppendUvarint(b, 32768)
	return append(b, bytes.Repeat([]byte{byte(i)}, 32768)...)
}
func framed(b []byte) []byte {
	h := make([]byte, 5)
	binary.BigEndian.PutUint32(h[1:], uint32(len(b)))
	return append(h, b...)
}
func serve(profile string) {
	protocols := new(http.Protocols)
	port := "8182"
	if profile == "sail" {
		protocols.SetUnencryptedHTTP2(true)
		port = "50052"
	} else {
		protocols.SetHTTP1(true)
	}
	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		body, e := io.ReadAll(io.LimitReader(r.Body, 1<<20))
		if e != nil {
			http.Error(w, "body", 400)
			return
		}
		if profile == "lakekeeper" {
			if r.ProtoMajor != 1 || r.ProtoMinor != 1 {
				http.Error(w, "HTTP/1.1 required", 400)
				return
			}
			w.Header().Set("Content-Type", "application/json")
			must(json.NewEncoder(w).Encode(map[string]string{"method": r.Method, "uri": r.RequestURI, "host": r.Host, "body": string(body), "proto": r.Header.Get("X-Forwarded-Proto"), "forwarded": r.Header.Get("Forwarded"), "xff": r.Header.Get("X-Forwarded-For"), "request_id": r.Header.Get("X-Request-ID")}))
			return
		}
		if r.ProtoMajor != 2 || r.Method != "POST" || r.Header.Get("Content-Type") != "application/grpc" || r.Header.Get("Te") != "trailers" || !bytes.Equal(body, framed(nil)) {
			http.Error(w, "invalid gRPC request", 400)
			return
		}
		count := 3
		switch r.URL.Path {
		case "/rehearsal.Stream/Short":
		case "/rehearsal.Stream/Long":
			count = 128
		case "/rehearsal.Stream/Fail":
		default:
			http.Error(w, "unknown RPC", 404)
			return
		}
		w.Header().Set("Content-Type", "application/grpc")
		w.Header().Set("Trailer", "Grpc-Status, Grpc-Message, Rehearsal-Count")
		w.WriteHeader(200)
		flusher := w.(http.Flusher)
		for i := 0; i < count; i++ {
			if count == 128 && i == 1 {
				time.Sleep(65 * time.Second)
			} // exceeds default grpc_read_timeout
			if _, e = w.Write(framed(message(i))); e != nil {
				return
			}
			flusher.Flush()
		}
		w.Header().Set("Grpc-Status", "0")
		if strings.HasSuffix(r.URL.Path, "/Fail") {
			w.Header().Set("Grpc-Status", "7")
			w.Header().Set("Grpc-Message", "denied")
		}
		w.Header().Set("Rehearsal-Count", strconv.Itoa(count))
	})
	server := &http.Server{Addr: "127.0.0.1:" + port, Handler: handler, Protocols: protocols, ReadHeaderTimeout: 5 * time.Second}
	log.Fatal(server.ListenAndServe())
}

func check(profile, origin, caFile, expected, mode string) {
	roots := x509.NewCertPool()
	ca, e := os.ReadFile(caFile)
	must(e)
	require(roots.AppendCertsFromPEM(ca), "invalid CA")
	protocols := new(http.Protocols)
	if profile == "sail" {
		protocols.SetHTTP2(true)
	} else {
		protocols.SetHTTP1(true)
	}
	config := &tls.Config{RootCAs: roots, MinVersion: tls.VersionTLS12}
	if mode == "tls12" {
		config.MaxVersion = tls.VersionTLS12
	}
	if mode == "tls13" {
		config.MinVersion = tls.VersionTLS13
	}
	transport := &http.Transport{TLSClientConfig: config, Protocols: protocols}
	defer transport.CloseIdleConnections()
	client := &http.Client{Transport: transport, Timeout: 100 * time.Second, CheckRedirect: func(_ *http.Request, _ []*http.Request) error { return errors.New("unexpected redirect") }}
	path := "/catalog/echo?canary=query-private"
	payload := []byte("body-private")
	if profile == "sail" {
		path = "/rehearsal.Stream/Short"
		payload = framed(nil)
		if mode == "long" {
			path = "/rehearsal.Stream/Long"
		}
		if mode == "status" {
			path = "/rehearsal.Stream/Fail"
		}
	}
	req, e := http.NewRequest("POST", origin+path, bytes.NewReader(payload))
	must(e)
	req.Header.Set("X-Forwarded-For", "spoofed")
	req.Header.Set("X-Forwarded-Proto", "http")
	req.Header.Set("Forwarded", "for=spoofed")
	req.Header.Set("X-Request-ID", "rehearsal.valid")
	if profile == "sail" {
		req.Header.Set("Content-Type", "application/grpc")
		req.Header.Set("Te", "trailers")
	}
	start := time.Now()
	resp, e := client.Do(req)
	if expected != "ok" {
		if resp != nil {
			resp.Body.Close()
		}
		require(e != nil, "negative unexpectedly succeeded")
		var unknown x509.UnknownAuthorityError
		var hostname x509.HostnameError
		var invalid x509.CertificateInvalidError
		switch expected {
		case "ca":
			require(errors.As(e, &unknown), "expected unknown CA: "+e.Error())
		case "hostname":
			require(errors.As(e, &hostname), "expected hostname rejection: "+e.Error())
		case "expired":
			require(errors.As(e, &invalid) && invalid.Reason == x509.Expired, "expected expiry rejection: "+e.Error())
		default:
			log.Fatal("unknown expectation")
		}
		fmt.Printf("PASS %s %s: %v\n", profile, expected, e)
		return
	}
	must(e)
	defer resp.Body.Close()
	require(resp.StatusCode == 200, "unexpected HTTP status: "+resp.Status)
	require(resp.TLS != nil && len(resp.TLS.VerifiedChains) > 0, "missing verified TLS chain")
	if profile == "lakekeeper" {
		var echo map[string]string
		must(json.NewDecoder(resp.Body).Decode(&echo))
		require(echo["method"] == "POST" && echo["uri"] == path && echo["body"] == string(payload) && echo["host"] == req.URL.Host, "HTTP request altered")
		require(echo["proto"] == "https" && echo["forwarded"] == "" && echo["xff"] != "spoofed" && net.ParseIP(echo["xff"]) != nil && echo["request_id"] == "rehearsal.valid", "forwarding headers incorrect")
	} else {
		require(resp.ProtoMajor == 2 && resp.Header.Get("Content-Type") == "application/grpc", "not gRPC over HTTP/2")
		count := 3
		if mode == "long" {
			count = 128
		}
		for i := 0; i < count; i++ {
			header := make([]byte, 5)
			_, e = io.ReadFull(resp.Body, header)
			must(e)
			want := message(i)
			require(header[0] == 0 && binary.BigEndian.Uint32(header[1:]) == uint32(len(want)), "invalid gRPC frame")
			got := make([]byte, len(want))
			_, e = io.ReadFull(resp.Body, got)
			must(e)
			require(bytes.Equal(got, want), "stream message reordered/truncated/corrupted")
			if mode == "long" && i == 0 {
				require(time.Since(start) < 30*time.Second, "first message buffered")
			}
		}
		extra, e := io.ReadAll(resp.Body)
		must(e)
		require(len(extra) == 0, "extra stream bytes")
		status := "0"
		if mode == "status" {
			status = "7"
			require(resp.Trailer.Get("Grpc-Message") == "denied", "lost grpc-message trailer")
		}
		require(resp.Trailer.Get("Grpc-Status") == status && resp.Trailer.Get("Rehearsal-Count") == strconv.Itoa(count), "lost/corrupt gRPC trailers")
		if mode == "long" {
			require(time.Since(start) >= 65*time.Second, "idle gap not exercised")
		}
	}
	fmt.Printf("PASS %s %s: verified TLS %x, %s, %.1fs\n", profile, mode, resp.TLS.Version, resp.Proto, time.Since(start).Seconds())
}
func probe(address, expected string) {
	conn, e := net.DialTimeout("tcp", address, 3*time.Second)
	if conn != nil {
		conn.Close()
	}
	if expected == "closed" {
		require(errors.Is(e, syscall.ECONNREFUSED), fmt.Sprintf("expected connection refused at %s, got %v", address, e))
	} else {
		must(e)
	}
	fmt.Println("PASS TCP", address, expected)
}
func plaintext(address, protocol string) {
	var resp *http.Response
	var e error
	if protocol == "h2c" {
		// Send the HTTP/2 connection preface and an empty SETTINGS frame.
		// A TLS-only NGINX listener answers with an HTTP/1 protocol error.
		// Read that response directly: Go HTTP/2 versions report its first
		// bytes differently (e.g. "frame too large"), which is not an oracle.
		conn, err := net.DialTimeout("tcp", address, 5*time.Second)
		must(err)
		defer conn.Close()
		must(conn.SetDeadline(time.Now().Add(5 * time.Second)))
		_, e = conn.Write(append([]byte("PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"), 0, 0, 0, 4, 0, 0, 0, 0, 0))
		must(e)
		resp, e = http.ReadResponse(bufio.NewReader(conn), nil)
	} else {
		client := &http.Client{Timeout: 5 * time.Second, CheckRedirect: func(_ *http.Request, _ []*http.Request) error { return http.ErrUseLastResponse }}
		resp, e = client.Post("http://"+address+"/rehearsal.Stream/Short", "application/grpc", bytes.NewReader(framed(nil)))
	}
	must(e)
	defer resp.Body.Close()
	body, e := io.ReadAll(resp.Body)
	must(e)
	require(resp.StatusCode == 400 && resp.Header.Get("Location") == "" &&
		resp.Header.Get("Content-Type") == "text/html" && bytes.Contains(body, []byte("<center>nginx</center>")),
		"plaintext did not receive an NGINX protocol-error response")
	if protocol == "http1" {
		require(bytes.Contains(body, []byte("plain HTTP request was sent to HTTPS port")), "plaintext reached application")
	}
	fmt.Println("PASS plaintext", protocol, "refused", address)
}
func listeners(port, backend string) {
	publicPort, e := strconv.Atoi(port)
	must(e)
	backendPort, e := strconv.Atoi(backend)
	must(e)
	expected := map[string]bool{
		fmt.Sprintf("tcp/00000000:%04X", publicPort):                          false,
		fmt.Sprintf("tcp6/00000000000000000000000000000000:%04X", publicPort): false,
		fmt.Sprintf("tcp/0100007F:%04X", backendPort):                         false,
	}
	for _, family := range []string{"tcp", "tcp6"} {
		raw, e := os.ReadFile("/proc/net/" + family)
		must(e)
		for _, line := range strings.Split(string(raw), "\n")[1:] {
			fields := strings.Fields(line)
			if len(fields) < 4 || fields[3] != "0A" {
				continue
			}
			socket := family + "/" + fields[1]
			_, ok := expected[socket]
			require(ok, "unexpected listening socket: "+socket)
			expected[socket] = true
		}
	}
	for socket, found := range expected {
		require(found, "missing listening socket: "+socket)
	}
	fmt.Println("PASS socket inventory: TLS on IPv4/IPv6, backend on 127.0.0.1 only")
}

func security() {
	status, e := os.ReadFile("/proc/1/status")
	must(e)
	for _, line := range strings.Split(string(status), "\n") {
		f := strings.Fields(line)
		if len(f) < 2 {
			continue
		}
		switch f[0] {
		case "Uid:":
			for _, uid := range f[1:] {
				require(uid != "0", "root process")
			}
		case "CapEff:":
			require(f[1] == "0000000000000000", "effective capabilities")
		case "NoNewPrivs:":
			require(f[1] == "1", "no-new-privileges missing")
		}
	}
	e = os.WriteFile("/rootfs-write-probe", []byte("probe"), 0600)
	require(errors.Is(e, syscall.EROFS), fmt.Sprintf("rootfs not read-only: %v", e))
	fmt.Println("PASS restricted runtime")
}
func main() {
	log.SetFlags(0)
	switch os.Args[1] {
	case "pki":
		pki(os.Args[2])
	case "serve":
		serve(os.Args[2])
	case "check":
		check(os.Args[2], os.Args[3], os.Args[4], os.Args[5], os.Args[6])
	case "probe":
		probe(os.Args[2], os.Args[3])
	case "plaintext":
		plaintext(os.Args[2], os.Args[3])
	case "listeners":
		listeners(os.Args[2], os.Args[3])
	case "security":
		security()
	default:
		log.Fatal("unknown command")
	}
}
