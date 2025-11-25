package w3g

import "fmt"

// ParseError is the base error type for parsing errors.
type ParseError struct {
	Message string
	Offset  *int
}

func (e *ParseError) Error() string {
	if e.Offset != nil {
		return fmt.Sprintf("%s at offset 0x%X", e.Message, *e.Offset)
	}
	return e.Message
}

// InvalidHeaderError indicates invalid or unrecognized header format.
type InvalidHeaderError struct {
	ParseError
}

// UnsupportedVersionError indicates replay version not supported.
type UnsupportedVersionError struct {
	ParseError
	Version string
}

// DecompressionError indicates failed to decompress data block.
type DecompressionError struct {
	ParseError
}

// UnknownActionError indicates unknown action type encountered.
type UnknownActionError struct {
	ParseError
	ActionID uint8
}

// TruncatedDataError indicates data was truncated unexpectedly.
type TruncatedDataError struct {
	ParseError
}

// Helper functions for creating errors

func newInvalidHeaderError(msg string) *InvalidHeaderError {
	return &InvalidHeaderError{ParseError{Message: msg}}
}

func newUnsupportedVersionError(version string) *UnsupportedVersionError {
	return &UnsupportedVersionError{
		ParseError: ParseError{Message: fmt.Sprintf("unsupported replay version: %s", version)},
		Version:    version,
	}
}

func newDecompressionError(msg string, offset int) *DecompressionError {
	return &DecompressionError{ParseError{Message: msg, Offset: &offset}}
}

func newUnknownActionError(actionID uint8, offset int) *UnknownActionError {
	return &UnknownActionError{
		ParseError: ParseError{
			Message: fmt.Sprintf("unknown action type 0x%02X", actionID),
			Offset:  &offset,
		},
		ActionID: actionID,
	}
}

func newTruncatedDataError(msg string, offset int) *TruncatedDataError {
	return &TruncatedDataError{ParseError{Message: msg, Offset: &offset}}
}
