"""Configuration management for eBis Cloud API."""

import os


BASE_URL = os.environ.get("EBIS_BASE_URL", "https://ia.ebis5.com/api/integration/external")
USERNAME = os.environ.get("EBIS_USERNAME", "IslanderAvApiAccess")
PASSWORD = os.environ.get("EBIS_PASSWORD", "A0606045-CB8F-46F6-A6BE-355A73455541")
