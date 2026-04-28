package main

import (
	"fmt"
	"net/http"
	"time"
)

func HandleRequest(w http.ResponseWriter, r *http.Request) {
	time.Sleep(5 * time.Second) // BPM-L001: blocking sleep
	fmt.Fprintf(w, "done")
}

func ProcessData(items []string) error { // BPM-L002: missing context.Context
	for _, item := range items {
		fmt.Println(item)
	}
	return nil
}

func FetchExternal(url string) { // BPM-L002: missing context
	panic("not implemented") // BPM-L013: panic in library
}

// Should NOT trigger BPM-L002 (has context)
func GetUser(ctx context.Context, id int) error {
	return nil
}

// Should NOT trigger BPM-L002 (unexported)
func helperFunc(x int) int {
	return x + 1
}
