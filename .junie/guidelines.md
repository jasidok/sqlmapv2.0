# SQLMap Development Guidelines

## Project Overview

SQLMap is an open-source penetration testing tool that automates the process of detecting and exploiting SQL injection
flaws. This document provides essential information for developers working on the project.

## Build and Configuration

### Python Requirements

- **Minimum Version**: Python 3.11+ (upgrading from current 2.6+ support)
- **Current Version Check**: Located in `lib/utils/versioncheck.py`
- **Version Constant**: Defined in `lib/core/settings.py` as `VERSION = "1.9.5.22"`

### Dependencies

SQLMap is designed to be self-contained with minimal external dependencies:

- **Bundled Libraries**: All required third-party libraries are included in `thirdparty/`
- **No pip requirements**: The project intentionally avoids external pip dependencies
- **Standard Library**: Heavy reliance on Python standard library modules

### Build Process

```bash
# No build process required - SQLMap runs directly from source
python sqlmap.py --help

# For development, ensure all core extensions are available
python -c "import bz2, gzip, pyexpat, ssl, sqlite3, zlib"
```

## Testing Information

### Running Tests

#### Smoke Test

```bash
# Basic functionality test - imports all modules and runs doctest
python sqlmap.py --smoke-test

# Expected output: "smoke test final result: PASSED"
```

#### Vulnerability Test

```bash
# Comprehensive test against built-in vulnerable server
python sqlmap.py --vuln-test

# This test:
# - Starts a local vulnerable server
# - Runs 38+ test cases covering various injection techniques
# - Tests different tamper scripts and techniques
# - Validates against multiple scenarios
```

#### Basic Import Test

```bash
# Simple test to ensure core modules can be imported
python -c "import sqlmap; import sqlmapapi"
```

### Test Framework Details

#### Smoke Test (`lib/core/testing.py::smokeTest()`)

- **Purpose**: Validates that all modules can be imported without errors
- **Process**: Walks through all .py files and imports them
- **Validation**: Runs doctests on all imported modules
- **Coverage**: Tests regex compilation in error XML files

#### Vulnerability Test (`lib/core/testing.py::vulnTest()`)

- **Purpose**: End-to-end testing against a controlled vulnerable application
- **Server**: Uses `extra/vulnserver/vulnserver.py` as test target
- **Database**: Creates temporary SQLite database with test schema
- **Test Cases**: 38+ predefined test scenarios covering:
    - Boolean-based blind injection
    - Time-based blind injection
    - Union-based injection
    - Error-based injection
    - Various tamper scripts
    - Different request methods (GET, POST, PUT)
    - Custom headers and authentication

#### Adding New Tests

1. **Unit Tests**: Add doctests to module docstrings
2. **Integration Tests**: Add test cases to `TESTS` tuple in `vulnTest()`
3. **Test Format**: `(command_line_options, expected_output_patterns)`

### Test Configuration

- **Temporary Files**: Tests create temporary files for requests, configs, databases
- **Network**: Tests use random local ports to avoid conflicts
- **Timeout**: Tests use `--time-sec=1` for faster execution
- **Database**: SQLite-based test database with predefined schema

## Code Style and Architecture

### Directory Structure

```
sqlmap/
├── sqlmap.py              # Main entry point
├── sqlmapapi.py           # REST API server
├── lib/                   # Core library modules
│   ├── core/              # Core functionality
│   ├── techniques/        # Injection techniques
│   ├── utils/             # Utility functions
│   ├── controller/        # Main controller logic
│   ├── request/           # HTTP request handling
│   └── takeover/          # OS takeover functionality
├── plugins/               # Database-specific plugins
├── tamper/                # Payload tampering scripts
├── thirdparty/            # Bundled third-party libraries
├── data/                  # Data files (XML, wordlists, etc.)
├── extra/                 # Additional tools and utilities
└── doc/                   # Documentation
```

### Coding Conventions

#### Python Version Compatibility

- **Current**: Supports Python 2.6+ (legacy)
- **Target**: Migrating to Python 3.11+ minimum
- **Compatibility Layer**: `lib/core/compat.py` handles version differences

#### String Formatting

- **Legacy**: Mix of `%` formatting and `.format()`
- **Target**: Migrate to f-strings for Python 3.11+

#### Import Style

- **Future Imports**: Currently uses `from __future__ import` statements
- **Standard Imports**: Group by standard library, third-party, local
- **Dynamic Imports**: Used for optional functionality and plugin loading

#### Error Handling

- **Custom Exceptions**: Defined in `lib/core/exception.py`
- **Error Messages**: Centralized in various modules with specific prefixes
- **Graceful Degradation**: Continue operation when possible

### Configuration Management

- **Main Config**: `sqlmap.conf` - Default configuration template
- **Runtime Config**: `lib/core/data.py::conf` - Runtime configuration object
- **Command Line**: Parsed in `lib/parse/cmdline.py`
- **Options**: Defined in `lib/core/optiondict.py`

### Database Support

- **Plugins**: Database-specific code in `plugins/dbms/`
- **Queries**: XML files in `data/xml/` define database-specific queries
- **Detection**: Automatic DBMS detection through fingerprinting

### Payload System

- **Techniques**: Different injection techniques in `lib/techniques/`
- **Tampers**: Payload modification scripts in `tamper/`
- **XML Definitions**: Payloads defined in `data/xml/payloads/`

## Performance Considerations

### Threading

- **Controller**: Multi-threaded request handling
- **Limitation**: Maximum threads controlled by `MAX_NUMBER_OF_THREADS`
- **Thread Safety**: Uses thread-local storage for isolation

### Memory Management

- **Large Data**: Uses `BigArray` for memory-efficient large data handling
- **Caching**: Various caching mechanisms for performance
- **Cleanup**: Automatic cleanup of temporary files and resources

### Network Optimization

- **Keep-Alive**: HTTP connection reuse when possible
- **Compression**: Automatic handling of compressed responses
- **Timeouts**: Configurable timeouts for different operations

## Security Considerations

### Input Validation

- **User Input**: All user input is validated and sanitized
- **File Operations**: Safe file handling with proper path validation
- **Command Execution**: Careful handling of system commands

### Output Sanitization

- **Sensitive Data**: Masking of sensitive information in logs
- **File Dumps**: Safe file writing with proper permissions
- **Error Messages**: No information disclosure in error messages

### Cryptographic Operations

- **Hashing**: Used for various authentication bypass techniques
- **Encryption**: Support for encrypted database connections
- **Random**: Secure random number generation for session handling

## Debugging and Development

### Logging

- **Levels**: CRITICAL, ERROR, WARNING, INFO, DEBUG
- **Output**: Console and optional file output
- **Verbosity**: Controlled by `-v` flags (1-6 levels)

### Debug Mode

- **Enable**: `--debug` flag
- **Output**: Additional debug information
- **Traffic**: HTTP request/response logging with `--traffic-file`

### Development Tools

- **API**: REST API mode with `--api` for integration testing
- **Shell**: Interactive shell mode with `--sql-shell`
- **Wizard**: Guided mode with `--wizard` for beginners

## Common Development Patterns

### Plugin Development

1. Create plugin file in `plugins/dbms/[database]/`
2. Implement required functions (banner, users, passwords, etc.)
3. Add database queries to `data/xml/queries.xml`
4. Test with specific database instances

### Tamper Script Development

1. Create script in `tamper/` directory
2. Implement `dependencies()` and `tamper()` functions
3. Add priority and requirements information
4. Test with various payloads and scenarios

### Adding New Techniques

1. Create technique module in `lib/techniques/`
2. Implement detection and exploitation logic
3. Add payload definitions to XML files
4. Update technique enumeration and selection logic

## Modernization Notes (Python 3.11+ Upgrade)

### Compatibility Removal

- Remove `from __future__ import` statements
- Update `lib/core/compat.py` for Python 3.11+ only
- Remove Python 2.x specific code paths

### Modern Python Features

- Use f-strings for string formatting
- Implement dataclasses for configuration objects
- Add type hints for better IDE support
- Use pathlib for file operations

### Performance Improvements

- Leverage Python 3.11+ performance enhancements
- Use `functools.lru_cache` for expensive operations
- Implement async patterns for network operations

This document should be updated as the codebase evolves and new patterns emerge.