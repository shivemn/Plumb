# encode/httpx

Commit 7cff5f7. Kind: library. Written by openrouter:nvidia/nemotron-3-ultra-550b-a55b:free.
26 of 28 claims kept after checking them against the code.

## Overview

- This is a library repository with a package definition whose only command needs an optional extra. ([f1](#f1))
- It is built with Python across 23 source files totaling 8,827 lines. ([f2](#f2))
- The project includes build or deploy files pyproject.toml and requirements.txt. ([f6](#f6), [f7](#f7))
- GitHub Actions workflows are present at .github/workflows/publish.yml and .github/workflows/test-suite.yml. ([f4](#f4), [f5](#f5))

## What it lets your code do

- The library exposes 10 public functions for making HTTP requests: delete, get, head, options, patch, post, put, request, stream, and create_ssl_context. ([f13](#f13), [f14](#f14), [f15](#f15), [f16](#f16), [f17](#f17), [f18](#f18), [f19](#f19), [f20](#f20), [f21](#f21), [f22](#f22), [f23](#f23))
- The delete, get, head, options, patch, post, and put functions send HTTP requests using their respective methods. ([f14](#f14), [f15](#f15), [f16](#f16), [f17](#f17), [f18](#f18), [f19](#f19), [f20](#f20))
- The request function sends an HTTP request with a configurable method. ([f21](#f21))
- The stream function is an alternative to request that streams the response body instead of loading it into memory at once. ([f22](#f22))
- The create_ssl_context function creates an SSL context for verified connections. ([f23](#f23))
- Client and AsyncClient provide synchronous and asynchronous HTTP clients with connection pooling, HTTP/2, redirects, and cookie persistence. ([f25](#f25), [f28](#f28))
- ASGITransport and WSGITransport are custom transports for sending requests directly to ASGI and WSGI applications respectively. ([f24](#f24), [f38](#f38))
- AsyncHTTPTransport, BaseTransport, and AsyncBaseTransport are transport base classes for custom connection handling. ([f39](#f39), [f41](#f41), [f42](#f42))
- Auth is the base class for authentication schemes, with BasicAuth for HTTP Basic authentication, FunctionAuth for callable authentication, and NetRCAuth for netrc file credentials. ([f26](#f26), [f27](#f27), [f31](#f31), [f34](#f34))
- Headers provides case-insensitive multi-dict HTTP headers, Cookies provides mutable mapping HTTP cookies, and QueryParams provides multi-dict URL query parameters. ([f30](#f30), [f32](#f32), [f35](#f35))
- URL breaks down URL components. ([f37](#f37))
- Timeout configures timeout behavior and Limits configures limits on client behaviors. ([f33](#f33), [f36](#f36))
- codes provides HTTP status codes and reason phrases. ([f29](#f29))
- ByteStream and AsyncByteStream handle synchronous and asynchronous byte streaming. ([f40](#f40), [f43](#f43))

## Code map

- The repository contains 23 Python source files totaling 8,827 lines. ([f2](#f2))
- The httpx package and httpx/_transports package have mutual dependencies, with httpx/_transports referencing httpx 12 times and httpx referencing httpx/_transports 3 times. ([f67](#f67), [f68](#f68), [f71](#f71))
- The test directory references httpx 17 times, and tests/client references httpx 10 times. ([f69](#f69), [f70](#f70))
- The most depended-upon file is httpx/__init__.py, used by 32 other files. ([f72](#f72))
- Other core modules with high usage include httpx/_models.py used by 13 files, httpx/_types.py used by 12 files, httpx/_exceptions.py used by 9 files, and httpx/_urls.py used by 8 files. ([f73](#f73), [f74](#f74), [f75](#f75), [f76](#f76))

## Hot spots

Nothing in this section could be supported by what was found.

## How to contribute

- The repository has two contribution guides at .github/CONTRIBUTING.md and docs/contributing.md. ([f45](#f45), [f58](#f58))
- CI runs scripts/install to install dependencies, scripts/check for linting, scripts/test for tests, and scripts/coverage to enforce coverage. ([f52](#f52), [f55](#f55), [f56](#f56), [f57](#f57))
- Recently closed pull requests were merged a median of 2 hours after opening, with first review a median of 2 hours after opening. ([f65](#f65), [f66](#f66))

## Sources

- <a id="f1"></a>**f1**: Looks like a library repo: a package definition whose only command needs an optional extra. `httpx/_main.py` line 313; `pyproject.toml` line 59
- <a id="f2"></a>**f2**: 23 source files in python, 8,827 lines in all. `httpx/_client.py`; `httpx/_models.py`; `httpx/_urls.py`
- <a id="f4"></a>**f4**: GitHub Actions workflow .github/workflows/publish.yml. `.github/workflows/publish.yml`
- <a id="f5"></a>**f5**: GitHub Actions workflow .github/workflows/test-suite.yml. `.github/workflows/test-suite.yml`
- <a id="f6"></a>**f6**: Build or deploy file pyproject.toml. `pyproject.toml`
- <a id="f7"></a>**f7**: Build or deploy file requirements.txt. `requirements.txt`
- <a id="f13"></a>**f13**: httpx/__init__.py makes 67 names public for code that uses httpx: 10 functions, 27 classes, 2 names, 28 exceptions. `httpx/__init__.py`
- <a id="f14"></a>**f14**: Public function delete(url, *, params, headers, cookies, auth, proxy, follow_redirects, timeout, verify, trust_env) in httpx/_api.py: Sends a `DELETE` request. `httpx/_api.py` line 405; `httpx/__init__.py`
- <a id="f15"></a>**f15**: Public function get(url, *, params, headers, cookies, auth, proxy, follow_redirects, verify, timeout, trust_env) in httpx/_api.py: Sends a `GET` request. `httpx/_api.py` line 174; `httpx/__init__.py`
- <a id="f16"></a>**f16**: Public function head(url, *, params, headers, cookies, auth, proxy, follow_redirects, verify, timeout, trust_env) in httpx/_api.py: Sends a `HEAD` request. `httpx/_api.py` line 246; `httpx/__init__.py`
- <a id="f17"></a>**f17**: Public function options(url, *, params, headers, cookies, auth, proxy, follow_redirects, verify, timeout, trust_env) in httpx/_api.py: Sends an `OPTIONS` request. `httpx/_api.py` line 210; `httpx/__init__.py`
- <a id="f18"></a>**f18**: Public function patch(url, *, content, data, files, json, params, headers, cookies, auth, proxy, follow_redirects, verify, timeout, trust_env) in httpx/_api.py: Sends a `PATCH` request. `httpx/_api.py` line 364; `httpx/__init__.py`
- <a id="f19"></a>**f19**: Public function post(url, *, content, data, files, json, params, headers, cookies, auth, proxy, follow_redirects, verify, timeout, trust_env) in httpx/_api.py: Sends a `POST` request. `httpx/_api.py` line 282; `httpx/__init__.py`
- <a id="f20"></a>**f20**: Public function put(url, *, content, data, files, json, params, headers, cookies, auth, proxy, follow_redirects, verify, timeout, trust_env) in httpx/_api.py: Sends a `PUT` request. `httpx/_api.py` line 323; `httpx/__init__.py`
- <a id="f21"></a>**f21**: Public function request(method, url, *, params, content, data, files, json, headers, cookies, auth, proxy, timeout, follow_redirects, verify, trust_env) in httpx/_api.py: Sends an HTTP request. `httpx/_api.py` line 39; `httpx/__init__.py`
- <a id="f22"></a>**f22**: Public function stream(method, url, *, params, content, data, files, json, headers, cookies, auth, proxy, timeout, follow_redirects, verify, trust_env) in httpx/_api.py: Alternative to `httpx.request()` that streams the response body instead of loading it into memory at once. `httpx/_api.py` line 123; `httpx/__init__.py`
- <a id="f23"></a>**f23**: Public function create_ssl_context(verify, cert, trust_env) in httpx/_config.py. `httpx/_config.py` line 23; `httpx/__init__.py`
- <a id="f24"></a>**f24**: Public class ASGITransport in httpx/_transports/asgi.py: A custom AsyncTransport that handles sending requests directly to an ASGI app. `httpx/_transports/asgi.py` line 63; `httpx/__init__.py`
- <a id="f25"></a>**f25**: Public class AsyncClient in httpx/_client.py: An asynchronous HTTP client, with connection pooling, HTTP/2, redirects, cookie persistence, etc. `httpx/_client.py` line 1307; `httpx/__init__.py`
- <a id="f26"></a>**f26**: Public class Auth in httpx/_auth.py: Base class for all authentication schemes. `httpx/_auth.py` line 22; `httpx/__init__.py`
- <a id="f27"></a>**f27**: Public class BasicAuth in httpx/_auth.py: Allows the 'auth' argument to be passed as a (username, password) pair, and uses HTTP Basic authentication. `httpx/_auth.py` line 126; `httpx/__init__.py`
- <a id="f28"></a>**f28**: Public class Client in httpx/_client.py: An HTTP client, with connection pooling, HTTP/2, redirects, cookie persistence, etc. `httpx/_client.py` line 594; `httpx/__init__.py`
- <a id="f29"></a>**f29**: Public class codes in httpx/_status_codes.py: HTTP status codes and reason phrases. `httpx/_status_codes.py` line 8; `httpx/__init__.py`
- <a id="f30"></a>**f30**: Public class Cookies in httpx/_models.py: HTTP Cookies, as a mutable mapping. `httpx/_models.py` line 1079; `httpx/__init__.py`
- <a id="f31"></a>**f31**: Public class FunctionAuth in httpx/_auth.py: Allows the 'auth' argument to be passed as a simple callable function, that takes the request, and returns a new,... `httpx/_auth.py` line 113; `httpx/__init__.py`
- <a id="f32"></a>**f32**: Public class Headers in httpx/_models.py: HTTP headers, as a case-insensitive multi-dict. `httpx/_models.py` line 139; `httpx/__init__.py`
- <a id="f33"></a>**f33**: Public class Limits in httpx/_config.py: Configuration for limits to various client behaviors. `httpx/_config.py` line 159; `httpx/__init__.py`
- <a id="f34"></a>**f34**: Public class NetRCAuth in httpx/_auth.py: Use a 'netrc' file to lookup basic auth credentials based on the url host. `httpx/_auth.py` line 145; `httpx/__init__.py`
- <a id="f35"></a>**f35**: Public class QueryParams in httpx/_urls.py: URL query parameters, as a multi-dict. `httpx/_urls.py` line 420; `httpx/__init__.py`
- <a id="f36"></a>**f36**: Public class Timeout in httpx/_config.py: Timeout configuration. `httpx/_config.py` line 72; `httpx/__init__.py`
- <a id="f37"></a>**f37**: Public class URL in httpx/_urls.py: The components of a URL are broken down like this:. `httpx/_urls.py` line 15; `httpx/__init__.py`
- <a id="f38"></a>**f38**: Public class WSGITransport in httpx/_transports/wsgi.py: A custom transport that handles sending requests directly to an WSGI app. `httpx/_transports/wsgi.py` line 44; `httpx/__init__.py`
- <a id="f39"></a>**f39**: Public class AsyncBaseTransport in httpx/_transports/base.py. `httpx/_transports/base.py` line 65; `httpx/__init__.py`
- <a id="f40"></a>**f40**: Public class AsyncByteStream in httpx/_types.py. `httpx/_types.py` line 106; `httpx/__init__.py`
- <a id="f41"></a>**f41**: Public class AsyncHTTPTransport in httpx/_transports/default.py. `httpx/_transports/default.py` line 279; `httpx/__init__.py`
- <a id="f42"></a>**f42**: Public class BaseTransport in httpx/_transports/base.py. `httpx/_transports/base.py` line 14; `httpx/__init__.py`
- <a id="f43"></a>**f43**: Public class ByteStream in httpx/_content.py. `httpx/_content.py` line 31; `httpx/__init__.py`
- <a id="f45"></a>**f45**: Contribution guide .github/CONTRIBUTING.md has a section "Reporting Bugs". `.github/CONTRIBUTING.md` line 11
- <a id="f52"></a>**f52**: CI step "Install dependencies" in job Publish release of .github/workflows/publish.yml runs: scripts/install. `.github/workflows/publish.yml` line 22
- <a id="f55"></a>**f55**: CI step "Run linting checks" in job tests of .github/workflows/test-suite.yml runs: scripts/check. `.github/workflows/test-suite.yml` line 28
- <a id="f56"></a>**f56**: CI step "Run tests" in job tests of .github/workflows/test-suite.yml runs: scripts/test. `.github/workflows/test-suite.yml` line 32
- <a id="f57"></a>**f57**: CI step "Enforce coverage" in job tests of .github/workflows/test-suite.yml runs: scripts/coverage. `.github/workflows/test-suite.yml` line 34
- <a id="f58"></a>**f58**: Contribution guide docs/contributing.md has a section "Reporting Bugs or Other Issues". `docs/contributing.md` line 12
- <a id="f65"></a>**f65**: Recently closed pull requests were merged a median of 2 hours after being opened (9 merged pull requests measured). issue 3836; issue 3832; issue 3834
- <a id="f66"></a>**f66**: Their first review by someone other than the author came a median of 2 hours after opening (7 pull requests measured). issue 3836; issue 3832; issue 3834
- <a id="f67"></a>**f67**: Code in httpx/_transports uses code in httpx (12 references). `httpx/_transports/asgi.py` line 5; `httpx/_transports/asgi.py` line 6; `httpx/_transports/base.py` line 6
- <a id="f68"></a>**f68**: Code in httpx uses code in httpx/_transports (3 references). `httpx/__init__.py` line 10; `httpx/_client.py` line 31; `httpx/_client.py` line 32
- <a id="f69"></a>**f69**: Code in tests uses code in httpx (17 references). `tests/conftest.py` line 20; `tests/test_api.py` line 5; `tests/test_api.py` line 98
- <a id="f70"></a>**f70**: Code in tests/client uses code in httpx (10 references). `tests/client/test_async_client.py` line 8; `tests/client/test_auth.py` line 18; `tests/client/test_client.py` line 9
- <a id="f71"></a>**f71**: httpx and httpx/_transports each use the other. `httpx/__init__.py` line 10; `httpx/_transports/asgi.py` line 5
- <a id="f72"></a>**f72**: httpx/__init__.py is used by 32 other files. `httpx/__init__.py`; `httpx/_transports/default.py` line 36; `tests/client/test_async_client.py` line 8
- <a id="f73"></a>**f73**: httpx/_models.py is used by 13 other files. `httpx/_models.py`; `httpx/__init__.py` line 8; `httpx/_api.py` line 8
- <a id="f74"></a>**f74**: httpx/_types.py is used by 12 other files. `httpx/_types.py`; `httpx/__init__.py` line 11; `httpx/_api.py` line 9
- <a id="f75"></a>**f75**: httpx/_exceptions.py is used by 9 other files. `httpx/_exceptions.py`; `httpx/__init__.py` line 7; `httpx/_auth.py` line 11
- <a id="f76"></a>**f76**: httpx/_urls.py is used by 8 other files. `httpx/_urls.py`; `httpx/__init__.py` line 12; `httpx/_api.py` line 20

## Removed

These were written by the model and failed a check.

- "The library defines 28 public exceptions including CloseError, ConnectError, ConnectTimeout, CookieConflict, DecodingError, HTTPError, HTTPStatusError, InvalidURL, LocalProtocolError, NetworkError, PoolTimeout, ProtocolError, ProxyError, ReadError, and ReadTimeout." (api): states numbers its facts do not: 28
- "Both guides include sections for Reporting Bugs, Development, Testing and Linting, Documenting, Resolving Build/CI Failures, Releasing, and Development proxy setup." (contribute): names something its facts do not: Build/CI
