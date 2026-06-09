"""
collectors/savana.py
--------------------
Production-quality collector for the Savana e-commerce API.

Design decisions
~~~~~~~~~~~~~~~~

1. **`requests.Session` with retry**
   Savana is a third-party API we reverse-engineered — it *will* flake.
   A session with `HTTPAdapter` + `Retry` gives us automatic exponential
   backoff (3 retries on 429 / 500 / 502 / 503 / 504) without any manual
   sleep loops.  The session also reuses TCP connections across calls,
   shaving ~50-80 ms per request.

2. **Typed return values via Pydantic `Product`**
   Raw dicts leak implementation details into every downstream consumer.
   Returning `list[Product]` means every caller gets validated, typed data
   and any field rename in the API is absorbed here — nowhere else.

3. **Separate `_build_payload` helper**
   Payload construction is deterministic and easily unit-testable.
   Keeping it isolated from I/O means tests never need to mock HTTP.

4. **`parse_products` is a `@staticmethod`**
   It is a pure function (JSON in → Products out), so it carries no state.
   This makes it trivially importable for offline tests.

5. **Logging over print()**
   `logging.getLogger(__name__)` gives us hierarchical, filterable output
   that respects the app's log-level config instead of cluttering stdout.

6. **Custom `SavanaAPIError` exception**
   Callers can catch Savana-specific failures (`SavanaAPIError`) without
   accidentally swallowing unrelated `RequestExceptions`.

7. **Configurable timeouts & page size**
   Hardcoded timeouts are a production anti-pattern.  Exposing them as
   constructor args (with safe defaults) lets the service layer tune
   behaviour without touching collector internals.

8. **Pagination support in `search_products`**
   The API is page-based.  `search_products` handles exactly one page
   and exposes `page` / `page_size` params so the service layer can
   orchestrate multi-page fetches without the collector knowing about it.
"""

from __future__ import annotations

import logging
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from models.schemas import Product


# ---------------------------------------------------------------------------
# Module logger
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class SavanaAPIError(Exception):
    """Raised when the Savana API returns an unexpected / error response."""

    def __init__(self, message: str, status_code: Optional[int] = None, body: Optional[dict] = None):
        self.status_code = status_code
        self.body = body
        super().__init__(message)


# ---------------------------------------------------------------------------
# Collector
# ---------------------------------------------------------------------------

class SavanaCollector:
    """
    Collects fashion product data from the Savana marketplace API.

    Parameters
    ----------
    base_url     : Root URL of the Savana API (no trailing slash).
    timeout      : Per-request timeout in seconds.
    max_retries  : How many times to retry on transient failures.
    page_size    : Default number of products per page.

    Usage
    -----
    >>> collector = SavanaCollector()
    >>> products  = collector.search_products(goods_ids=["1859842"])
    >>> for p in products:
    ...     print(p.name, p.price)
    """

    # The exact endpoint path we reverse-engineered
    _SEARCH_PATH = "/n/api/buyer/sr/app/search/goodsInfo"

    def __init__(
        self,
        base_url: str = "https://api-shop-in.savana.com",
        timeout: float = 10.0,
        max_retries: int = 3,
        page_size: int = 20,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._page_size = page_size

        # -- Build a resilient HTTP session --------------------------------
        #
        # Why a session?
        #   • Connection pooling (reuses TLS handshake across requests)
        #   • Automatic retry with backoff on transient HTTP errors
        #   • Consistent headers across every request
        #
        self._session = requests.Session()

        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=0.5,                          # 0s → 0.5s → 1s
            status_forcelist=[429, 500, 502, 503, 504],  # retry these codes
            allowed_methods=["POST"],                    # Savana uses POST
            raise_on_status=False,                       # we handle status ourselves
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)

        # Headers that mimic a mobile app client — reverse-engineered APIs
        # often reject bare `python-requests` User-Agents.
        self._session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Drape/1.0 (Fashion AI Collector)",
        })

        logger.info(
            "SavanaCollector initialised  base_url=%s  timeout=%.1fs  "
            "max_retries=%d  page_size=%d",
            self._base_url, self._timeout, max_retries, self._page_size,
        )

    # ------------------------------------------------------------------ #
    # Public methods                                                       #
    # ------------------------------------------------------------------ #

    def search_products(
        self,
        goods_ids: list[str],
        *,
        page: int = 1,
        page_size: Optional[int] = None,
        sort_list: Optional[list[int]] = None,
        expected_price: str = "",
        front_cat_ids: Optional[list[int]] = None,
    ) -> list[Product]:
        """
        Search for products by one or more goods IDs.

        This is the primary entry point.  It builds the payload, calls the
        Savana API, validates the response, and returns typed `Product` models.

        Parameters
        ----------
        goods_ids       : One or more Savana goods-ID strings.
        page            : 1-indexed page number.
        page_size       : Results per page (defaults to constructor value).
        sort_list       : Savana sort-priority list (default [5, 1, 6]).
        expected_price  : Optional price filter string.
        front_cat_ids   : Optional list of front-end category IDs.

        Returns
        -------
        list[Product]   : Validated product models.

        Raises
        ------
        SavanaAPIError  : On HTTP or business-logic errors from the API.
        """
        payload = self._build_payload(
            goods_ids=goods_ids,
            page=page,
            page_size=page_size or self._page_size,
            sort_list=sort_list or [5, 1, 6],
            expected_price=expected_price,
            front_cat_ids=front_cat_ids or [],
        )

        logger.debug("search_products  payload=%s", payload)

        response_json = self._post(payload)
        products = self.parse_products(response_json)

        logger.info(
            "search_products  goods_ids=%s  page=%d  returned=%d products",
            goods_ids, page, len(products),
        )

        return products

    def get_similar_products(self, goods_id: int | str) -> list[Product]:
        """
        Convenience wrapper: fetch products similar to a single goods ID.

        Internally delegates to `search_products` with sensible defaults.

        Parameters
        ----------
        goods_id : A single Savana goods-ID (int or str).

        Returns
        -------
        list[Product]
        """
        return self.search_products(goods_ids=[str(goods_id)])

    @staticmethod
    def parse_products(response_json: dict) -> list[Product]:
        """
        Parse a raw Savana API response into a list of `Product` models.

        This is intentionally a static method so it can be tested in
        complete isolation — no HTTP, no session, no state.

        Parameters
        ----------
        response_json : The full JSON body returned by the API.

        Returns
        -------
        list[Product]

        Raises
        ------
        SavanaAPIError : If the response structure is malformed or missing.
        """
        # ── Validate top-level envelope ───────────────────────────────
        #
        # The API returns {"ret": 200, "msg": "ok", "data": {...}}.
        # Any other `ret` value is treated as a business-logic error.
        #
        ret_code = response_json.get("ret")
        if ret_code != 200:
            raise SavanaAPIError(
                f"Savana returned non-200 business code: ret={ret_code}, "
                f"msg={response_json.get('msg', 'unknown')}",
                status_code=ret_code,
                body=response_json,
            )

        data = response_json.get("data")
        if data is None:
            raise SavanaAPIError(
                "Savana response missing 'data' key",
                body=response_json,
            )

        goods_list: list[dict] = data.get("goodsList", [])

        # ── Map each raw dict → validated Product ─────────────────────
        products: list[Product] = []

        for item in goods_list:
            try:
                # Extract the first image thumbnail (if any)
                image_url: Optional[str] = None
                images = item.get("imageList") or []
                if images and isinstance(images[0], dict):
                    image_url = images[0].get("goodsThumb")

                product = Product(
                    id=int(item["goodsId"]),
                    name=item.get("goodsName", "Untitled"),
                    price=float(item.get("salePrice", 0)),
                    image=image_url,
                    brand=item.get("brandName"),
                    color=item.get("colorName"),
                    category=item.get("categoryName"),
                )
                products.append(product)

            except (KeyError, ValueError, TypeError) as exc:
                # Log and skip malformed items rather than crashing the
                # entire batch — partial results are better than none.
                logger.warning(
                    "Skipping malformed product entry: %s  error=%s",
                    item.get("goodsId", "?"),
                    exc,
                )

        return products

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _build_payload(
        goods_ids: list[str],
        page: int,
        page_size: int,
        sort_list: list[int],
        expected_price: str,
        front_cat_ids: list[int],
    ) -> dict:
        """
        Construct the JSON payload for the Savana search endpoint.

        Kept as a static method for two reasons:
          1. It is pure — no side effects, trivially testable.
          2. It documents the exact contract with the Savana API in one place.
        """
        return {
            "id": 1,
            "itemParam": {
                "expectedPrice": expected_price,
                "frontCatId": front_cat_ids,
                "goodsId": goods_ids,
                "sortList": sort_list,
            },
            "pageIndex": page,
            "pageSize": page_size,
            "nextPageSign": "",
            "scrollIdDifferent": "",
            "scrollIdSimilar": "",
            "visitedGoodsIdList": [],
            "filterGoodsIdList": [],
        }

    def _post(self, payload: dict) -> dict:
        """
        Send a POST request to the Savana search endpoint.

        Centralising the HTTP call here means:
          • Every request goes through the retry-enabled session.
          • Timeout is applied uniformly.
          • HTTP-level errors are translated into `SavanaAPIError`.
          • The raw JSON is returned for `parse_products` to handle.

        Raises
        ------
        SavanaAPIError : On network / HTTP errors.
        """
        url = f"{self._base_url}{self._SEARCH_PATH}"

        try:
            resp = self._session.post(url, json=payload, timeout=self._timeout)
        except requests.ConnectionError as exc:
            logger.error("Connection to Savana failed: %s", exc)
            raise SavanaAPIError(f"Connection failed: {exc}") from exc
        except requests.Timeout as exc:
            logger.error("Request to Savana timed out after %.1fs", self._timeout)
            raise SavanaAPIError(f"Request timed out: {exc}") from exc
        except requests.RequestException as exc:
            logger.error("Unexpected request error: %s", exc)
            raise SavanaAPIError(f"Request error: {exc}") from exc

        # Raise on 4xx / 5xx that survived the retry strategy
        if not resp.ok:
            logger.error(
                "Savana HTTP error  status=%d  body=%s",
                resp.status_code,
                resp.text[:500],
            )
            raise SavanaAPIError(
                f"HTTP {resp.status_code}: {resp.reason}",
                status_code=resp.status_code,
            )

        # Attempt to decode JSON
        try:
            return resp.json()
        except ValueError as exc:
            logger.error("Savana returned non-JSON body: %s", resp.text[:200])
            raise SavanaAPIError(
                f"Invalid JSON in response: {exc}",
                status_code=resp.status_code,
            ) from exc

    # ------------------------------------------------------------------ #
    # Context-manager support (optional, for graceful cleanup)             #
    # ------------------------------------------------------------------ #

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self._session.close()
        logger.debug("SavanaCollector session closed")

    def __enter__(self) -> SavanaCollector:
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def __repr__(self) -> str:
        return (
            f"SavanaCollector(base_url={self._base_url!r}, "
            f"timeout={self._timeout}, page_size={self._page_size})"
        )