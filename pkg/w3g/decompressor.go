package w3g

import (
	"bytes"
	"compress/flate"
	"compress/zlib"
	"encoding/binary"
	"fmt"
	"io"
)

// decompressBlocks decompresses all data blocks from reader.
//
// Block format varies by version:
//
// Classic (pre-Reforged) - 8 byte header:
//   - Offset 0x00: Compressed size (1 word)
//   - Offset 0x02: Decompressed size (1 word)
//   - Offset 0x04: Checksum/unknown (1 dword)
//   - Offset 0x08: Compressed data (compressed_size bytes, raw deflate)
//
// Reforged - 12 byte header:
//   - Offset 0x00: Compressed size (1 word) - doesn't include header
//   - Offset 0x02: Unknown (1 word)
//   - Offset 0x04: Decompressed size (1 dword)
//   - Offset 0x08: Checksum (1 dword)
//   - Offset 0x0C: Compressed data (zlib format with header)
func decompressBlocks(r io.Reader, header *ReplayHeader) ([]byte, error) {
	var result bytes.Buffer
	isReforged := header.IsReforged()

	for i := uint32(0); i < header.NumCompressedBlocks; i++ {
		var compressedSize uint32

		if isReforged {
			// Reforged: 12-byte header
			blockHeader := make([]byte, 12)
			if _, err := io.ReadFull(r, blockHeader); err != nil {
				return nil, newTruncatedDataError(
					fmt.Sprintf("block %d header truncated", i), result.Len(),
				)
			}
			compressedSize = uint32(binary.LittleEndian.Uint16(blockHeader[0:]))
			// decompressedSize is at offset 4 (4 bytes) but we don't need it
		} else {
			// Classic: 8-byte header
			blockHeader := make([]byte, 8)
			if _, err := io.ReadFull(r, blockHeader); err != nil {
				return nil, newTruncatedDataError(
					fmt.Sprintf("block %d header truncated", i), result.Len(),
				)
			}
			compressedSize = uint32(binary.LittleEndian.Uint16(blockHeader[0:]))
			// decompressedSize is at offset 2 (2 bytes) but we don't need it
		}

		// Read compressed data
		compressedData := make([]byte, compressedSize)
		if _, err := io.ReadFull(r, compressedData); err != nil {
			return nil, newTruncatedDataError(
				fmt.Sprintf("block %d data truncated: expected %d bytes", i, compressedSize),
				result.Len(),
			)
		}

		// Decompress
		var decompressed []byte
		var err error

		if isReforged {
			// Reforged uses zlib with header
			decompressed, err = decompressZlib(compressedData)
		} else {
			// Classic uses raw deflate
			decompressed, err = decompressDeflate(compressedData)
			if err != nil {
				// Fallback to zlib with header
				decompressed, err = decompressZlib(compressedData)
			}
		}

		if err != nil {
			return nil, newDecompressionError(
				fmt.Sprintf("block %d decompression failed: %v", i, err),
				result.Len(),
			)
		}

		result.Write(decompressed)
	}

	return result.Bytes(), nil
}

// decompressZlib decompresses data using zlib (with header).
func decompressZlib(data []byte) ([]byte, error) {
	r, err := zlib.NewReader(bytes.NewReader(data))
	if err != nil {
		return nil, err
	}
	defer r.Close()

	// Use a buffer to read the decompressed data
	// The W3G format doesn't always have proper zlib trailers,
	// so io.ReadAll may fail with "unexpected EOF"
	var result bytes.Buffer
	buf := make([]byte, 8192)
	for {
		n, err := r.Read(buf)
		if n > 0 {
			result.Write(buf[:n])
		}
		if err != nil {
			if err == io.EOF || err.Error() == "unexpected EOF" {
				break
			}
			// Only return error if we haven't read any data
			if result.Len() == 0 {
				return nil, err
			}
			break
		}
	}

	return result.Bytes(), nil
}

// decompressDeflate decompresses data using raw deflate (no header).
func decompressDeflate(data []byte) ([]byte, error) {
	r := flate.NewReader(bytes.NewReader(data))
	defer r.Close()

	return io.ReadAll(r)
}

// decompressSingleBlock decompresses a single block of data.
func decompressSingleBlock(data []byte, useZlibHeader bool) ([]byte, error) {
	if useZlibHeader {
		return decompressZlib(data)
	}

	decompressed, err := decompressDeflate(data)
	if err != nil {
		// Try the other format as fallback
		return decompressZlib(data)
	}
	return decompressed, nil
}
