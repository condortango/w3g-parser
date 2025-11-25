package w3g

import (
	"bytes"
	"encoding/binary"
	"fmt"
	"io"
)

// parseHeader parses the W3G file header from a reader.
//
// The header consists of:
// - Base header (0x30 bytes)
// - SubHeader (0x10 bytes for v0, 0x14 bytes for v1)
func parseHeader(r io.Reader) (*ReplayHeader, []byte, error) {
	// Read base header (48 bytes)
	baseHeader := make([]byte, BaseHeaderSize)
	if _, err := io.ReadFull(r, baseHeader); err != nil {
		return nil, nil, newTruncatedDataError("file too small for header", len(baseHeader))
	}

	// Validate magic string
	magic := baseHeader[:28]
	if !bytes.Equal(magic, MagicString) {
		return nil, nil, newInvalidHeaderError(
			fmt.Sprintf("invalid magic string: got %q", magic),
		)
	}

	// Parse base header fields using little-endian
	// Offset 0x1C: First data block offset (header size)
	// Offset 0x20: Compressed file size
	// Offset 0x24: Header version (0 or 1)
	// Offset 0x28: Decompressed data size
	// Offset 0x2C: Number of compressed blocks
	headerSize := binary.LittleEndian.Uint32(baseHeader[0x1C:])
	compressedSize := binary.LittleEndian.Uint32(baseHeader[0x20:])
	headerVersion := binary.LittleEndian.Uint32(baseHeader[0x24:])
	decompressedSize := binary.LittleEndian.Uint32(baseHeader[0x28:])
	numBlocks := binary.LittleEndian.Uint32(baseHeader[0x2C:])

	// Determine subheader size based on version
	var subHeaderSize int
	switch headerVersion {
	case 0:
		subHeaderSize = SubHeaderV0Size
	case 1:
		subHeaderSize = SubHeaderV1Size
	default:
		return nil, nil, newInvalidHeaderError(
			fmt.Sprintf("unknown header version: %d", headerVersion),
		)
	}

	// Read subheader
	subHeader := make([]byte, subHeaderSize)
	if _, err := io.ReadFull(r, subHeader); err != nil {
		return nil, nil, newTruncatedDataError("file too small for subheader", BaseHeaderSize)
	}

	header := &ReplayHeader{
		Magic:               magic,
		HeaderSize:          headerSize,
		CompressedSize:      compressedSize,
		HeaderVersion:       headerVersion,
		DecompressedSize:    decompressedSize,
		NumCompressedBlocks: numBlocks,
	}

	// Parse subheader based on version
	if headerVersion == 0 {
		// Version 0 (Classic, patches <= 1.06)
		// Offset 0x00: unknown (1 word, always 0)
		// Offset 0x02: version number (1 word)
		// Offset 0x04: build number (1 word)
		// Offset 0x06: flags (1 word)
		// Offset 0x08: duration (1 dword)
		// Offset 0x0C: CRC32 (1 dword)
		header.Version = uint32(binary.LittleEndian.Uint16(subHeader[0x02:]))
		header.BuildNumber = binary.LittleEndian.Uint16(subHeader[0x04:])
		header.Flags = binary.LittleEndian.Uint16(subHeader[0x06:])
		header.DurationMs = binary.LittleEndian.Uint32(subHeader[0x08:])
		header.CRC32 = binary.LittleEndian.Uint32(subHeader[0x0C:])
		header.GameIdentifier = GameIDClassic
	} else {
		// Version 1 (Expansion, patches >= 1.07)
		// Offset 0x00: game identifier (1 dword): 'WAR3' or 'W3XP'
		// Offset 0x04: version number (1 dword)
		// Offset 0x08: build number (1 word)
		// Offset 0x0A: flags (1 word)
		// Offset 0x0C: duration (1 dword)
		// Offset 0x10: CRC32 (1 dword)
		header.GameIdentifier = string(subHeader[0x00:0x04])
		header.Version = binary.LittleEndian.Uint32(subHeader[0x04:])
		header.BuildNumber = binary.LittleEndian.Uint16(subHeader[0x08:])
		header.Flags = binary.LittleEndian.Uint16(subHeader[0x0A:])
		header.DurationMs = binary.LittleEndian.Uint32(subHeader[0x0C:])
		header.CRC32 = binary.LittleEndian.Uint32(subHeader[0x10:])
	}

	rawHeader := append(baseHeader, subHeader...)
	header.RawHeader = rawHeader

	return header, rawHeader, nil
}

// parseHeaderFromBytes parses header from bytes.
func parseHeaderFromBytes(data []byte) (*ReplayHeader, error) {
	header, _, err := parseHeader(bytes.NewReader(data))
	return header, err
}
