"""
Dify Plugin Daemon Configuration

This module contains the configuration settings for the Dify Plugin Daemon,
mirroring the Go implementation's configuration structure.
"""

from typing import Optional, Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PlatformType = Literal["local", "aws_lambda", "serverless"]


class Config(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Server configuration
    server_host: str = Field(default="0.0.0.0", description="Server host to bind")
    server_port: int = Field(default=5001, ge=1, le=65535, description="Server port")
    server_key: str = Field(..., description="Server authentication key")

    # Admin API configuration
    admin_api_enabled: bool = Field(default=False, description="Enable admin API")
    admin_api_key: Optional[str] = Field(default=None, description="Admin API key")

    # Dify inner API configuration
    dify_inner_api_url: str = Field(..., description="Dify inner API URL")
    dify_inner_api_key: str = Field(..., description="Dify inner API key")

    # Storage configuration
    plugin_storage_type: str = Field(..., description="Plugin storage type (s3, local, etc.)")
    plugin_storage_oss_bucket: Optional[str] = Field(default=None, description="OSS bucket name")

    # AWS S3 configuration
    s3_use_aws_managed_iam: bool = Field(default=False, description="Use AWS managed IAM")
    s3_use_aws: bool = Field(default=True, description="Use AWS S3")
    s3_endpoint: Optional[str] = Field(default=None, description="S3 endpoint")
    s3_use_path_style: bool = Field(default=True, description="Use path style for S3")
    aws_access_key: Optional[str] = Field(default=None, description="AWS access key")
    aws_secret_key: Optional[str] = Field(default=None, description="AWS secret key")
    aws_region: Optional[str] = Field(default=None, description="AWS region")

    # Tencent COS configuration
    tencent_cos_secret_key: Optional[str] = Field(default=None, description="Tencent COS secret key")
    tencent_cos_secret_id: Optional[str] = Field(default=None, description="Tencent COS secret ID")
    tencent_cos_region: Optional[str] = Field(default=None, description="Tencent COS region")
    tencent_cos_endpoint: Optional[str] = Field(default=None, description="Tencent COS endpoint")

    # Azure Blob configuration
    azure_blob_storage_container_name: Optional[str] = Field(default=None, description="Azure blob container name")
    azure_blob_storage_connection_string: Optional[str] = Field(default=None, description="Azure blob connection string")

    # Aliyun OSS configuration
    aliyun_oss_region: Optional[str] = Field(default=None, description="Aliyun OSS region")
    aliyun_oss_endpoint: Optional[str] = Field(default=None, description="Aliyun OSS endpoint")
    aliyun_oss_access_key_id: Optional[str] = Field(default=None, description="Aliyun OSS access key ID")
    aliyun_oss_access_key_secret: Optional[str] = Field(default=None, description="Aliyun OSS access key secret")
    aliyun_oss_auth_version: str = Field(default="v4", description="Aliyun OSS auth version")
    aliyun_oss_path: Optional[str] = Field(default=None, description="Aliyun OSS path")
    aliyun_oss_cloudbox_id: Optional[str] = Field(default=None, description="Aliyun OSS cloudbox ID")

    # Google GCS configuration
    google_cloud_storage_credentials_b64: Optional[str] = Field(default=None, description="GCS credentials base64")

    # Huawei OBS configuration
    huawei_obs_access_key: Optional[str] = Field(default=None, description="Huawei OBS access key")
    huawei_obs_secret_key: Optional[str] = Field(default=None, description="Huawei OBS secret key")
    huawei_obs_server: Optional[str] = Field(default=None, description="Huawei OBS server")
    huawei_obs_path_style: bool = Field(default=False, description="Huawei OBS path style")

    # Volcengine TOS configuration
    volcengine_tos_endpoint: Optional[str] = Field(default=None, description="Volcengine TOS endpoint")
    volcengine_tos_access_key: Optional[str] = Field(default=None, description="Volcengine TOS access key")
    volcengine_tos_secret_key: Optional[str] = Field(default=None, description="Volcengine TOS secret key")
    volcengine_tos_region: Optional[str] = Field(default=None, description="Volcengine TOS region")

    # Local storage configuration
    plugin_storage_local_root: Optional[str] = Field(default=None, description="Local storage root path")

    # Plugin remote installing configuration
    plugin_remote_installing_host: Optional[str] = Field(default=None, description="Remote installing host")
    plugin_remote_installing_port: Optional[int] = Field(default=None, description="Remote installing port")
    plugin_remote_installing_enabled: bool = Field(default=True, description="Enable remote installing")
    plugin_remote_installing_max_conn: Optional[int] = Field(default=None, description="Max connections")
    plugin_remote_installing_max_single_tenant_conn: Optional[int] = Field(default=None, description="Max single tenant connections")
    plugin_remote_install_server_event_loop_nums: Optional[int] = Field(default=None, description="Event loop nums")

    # Plugin endpoint configuration
    plugin_endpoint_enabled: bool = Field(default=True, description="Enable plugin endpoint")

    # Plugin paths
    plugin_working_path: Optional[str] = Field(default=None, description="Plugin working path")
    plugin_media_cache_size: int = Field(default=100, description="Media cache size")
    plugin_asset_cache_size: int = Field(default=100, description="Asset cache size")
    plugin_media_cache_path: Optional[str] = Field(default=None, description="Media cache path")
    plugin_installed_path: str = Field(..., description="Plugin installed path")
    plugin_package_cache_path: Optional[str] = Field(default=None, description="Plugin package cache path")

    # Plugin timeout configuration
    plugin_max_execution_timeout: int = Field(..., description="Max execution timeout in seconds")
    plugin_install_timeout: int = Field(default=15, description="Plugin install timeout in minutes")
    plugin_local_launching_concurrent: int = Field(..., description="Local launching concurrent")

    # Platform type
    platform: PlatformType = Field(..., description="Platform type (local, aws_lambda, serverless)")

    # Routine pool
    routine_pool_size: int = Field(..., description="Routine pool size")

    # Redis configuration
    redis_host: Optional[str] = Field(default=None, description="Redis host")
    redis_port: Optional[int] = Field(default=None, description="Redis port")
    redis_password: Optional[str] = Field(default=None, description="Redis password")
    redis_username: Optional[str] = Field(default=None, description="Redis username")
    redis_db: int = Field(default=0, description="Redis database")
    redis_use_ssl: bool = Field(default=False, description="Use SSL for Redis")
    redis_ssl_cert_reqs: Optional[str] = Field(default=None, description="SSL cert requirements")
    redis_ssl_ca_certs: Optional[str] = Field(default=None, description="SSL CA certs")

    # Redis sentinel configuration
    redis_use_sentinel: bool = Field(default=False, description="Use Redis sentinel")
    redis_sentinels: Optional[str] = Field(default=None, description="Redis sentinels")
    redis_sentinel_service_name: Optional[str] = Field(default=None, description="Sentinel service name")
    redis_sentinel_username: Optional[str] = Field(default=None, description="Sentinel username")
    redis_sentinel_password: Optional[str] = Field(default=None, description="Sentinel password")
    redis_sentinel_socket_timeout: Optional[float] = Field(default=None, description="Sentinel socket timeout")

    # Database configuration
    db_type: str = Field(default="postgresql", description="Database type")
    db_username: str = Field(..., description="Database username")
    db_password: str = Field(..., description="Database password")
    db_host: str = Field(..., description="Database host")
    db_port: int = Field(..., ge=1, le=65535, description="Database port")
    db_database: str = Field(..., description="Database name")
    db_default_database: str = Field(..., description="Default database name")
    db_ssl_mode: str = Field(default="disable", description="SSL mode (disable, require)")

    # Database connection pool settings
    db_max_idle_conns: int = Field(default=10, description="Max idle connections")
    db_max_open_conns: int = Field(default=100, description="Max open connections")
    db_conn_max_lifetime: int = Field(default=3600, description="Connection max lifetime in seconds")
    db_conn_max_idle_time: int = Field(default=1800, description="Connection max idle time in seconds")

    # Logging configuration
    log_level: str = Field(default="info", description="Log level")
    log_output_format: str = Field(default="text", description="Log output format (text, json)")
    log_file: Optional[str] = Field(default=None, description="Log file path")

    # Health check API log
    health_api_log_enabled: bool = Field(default=True, description="Enable health API log")

    # Sentry configuration
    sentry_enabled: bool = Field(default=False, description="Enable Sentry")
    sentry_dsn: Optional[str] = Field(default=None, description="Sentry DSN")
    sentry_traces_sample_rate: float = Field(default=0.1, description="Sentry traces sample rate")

    # OpenTelemetry configuration
    enable_otel: bool = Field(default=False, description="Enable OpenTelemetry")
    otel_exporter_otlp_endpoint: Optional[str] = Field(default=None, description="OTLP endpoint")
    otel_service_name: Optional[str] = Field(default=None, description="Service name for OTEL")
    otel_traces_sample_rate: float = Field(default=0.1, description="OTEL traces sample rate")

    # Serverless configuration
    max_serverless_transaction_timeout: int = Field(default=300, description="Max serverless transaction timeout")

    @field_validator("server_key")
    @classmethod
    def validate_server_key(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("server_key is required and cannot be empty")
        return v

    @field_validator("admin_api_key")
    @classmethod
    def validate_admin_api_key(cls, v: Optional[str], info) -> Optional[str]:
        if v and len(v) < 10:
            raise ValueError("admin_api_key length must be greater than 10 when provided")
        return v

    def set_default(self) -> None:
        """Set default values for optional fields."""
        if self.log_level not in ["debug", "info", "warning", "error", "critical"]:
            self.log_level = "info"

    def validate(self) -> None:
        """Validate the configuration."""
        if self.admin_api_enabled and (not self.admin_api_key or len(self.admin_api_key) < 10):
            raise ValueError("admin_api_key is required and must be at least 10 characters when admin API is enabled")

        if self.db_type not in ["postgresql", "pgbouncer", "mysql", "oceanbase", "seekdb"]:
            raise ValueError(f"Invalid DB type: {self.db_type}")
