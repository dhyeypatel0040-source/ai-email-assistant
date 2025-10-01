"""
Composio connection management service.
"""
from typing import Dict, Any, List, Optional
from composio import Composio
from app.config.settings import get_settings
from app.models.auth import AuthConfig, SignInRequest, SignInResponse, UserConnectionStatus
from core.constants import DEFAULT_CALLBACK_URL


class ComposioConnectionService:
    """Service for managing Composio connections."""
    
    def __init__(self):
        """Initialize the connection service."""
        self.settings = get_settings()
        self.composio = Composio(api_key=self.settings.composio_api_key)
    
    def list_auth_configs(self) -> List[AuthConfig]:
        """List available auth configurations."""
        try:
            response = self.composio.auth_configs.list()
            return [
                AuthConfig(
                    id=config.id,
                    toolkit=config.toolkit.slug,
                    auth_type=config.auth_scheme,
                    status="active"
                )
                for config in response.items
            ]
        except Exception as e:
            raise Exception(f"Failed to list auth configs: {str(e)}")
    
    def get_gmail_auth_config(self) -> Optional[AuthConfig]:
        """Get Gmail auth configuration."""
        try:
            # Use the configured AUTH_CONFIG_ID if available
            if self.settings.auth_config_id:
                try:
                    config = self.composio.auth_configs.get(self.settings.auth_config_id)
                    return AuthConfig(
                        id=config.id,
                        toolkit=config.toolkit.slug,
                        auth_type=config.auth_scheme,
                        status="active"
                    )
                except Exception:
                    # Fall back to listing if specific config not found
                    pass
            
            # Fallback: Use toolkit_slug parameter to filter directly
            response = self.composio.auth_configs.list(toolkit_slug='gmail')
            if response.items:
                config = response.items[0]  # Get the first Gmail auth config
                return AuthConfig(
                    id=config.id,
                    toolkit=config.toolkit.slug,
                    auth_type=config.auth_scheme,
                    status="active"
                )
            return None
        except Exception as e:
            raise Exception(f"Failed to get Gmail auth config: {str(e)}")
    
    def check_user_connection(self, user_id: str) -> bool:
        """Check if user already has a connected account."""
        try:
            connections = self.composio.connected_accounts.list(entity_id=user_id)
            return len(connections) > 0
        except Exception as e:
            # If user doesn't exist or no connections, return False
            return False
    
    def create_sign_in_link(self, request: SignInRequest) -> SignInResponse:
        """Create a sign-in link for user email authentication."""
        try:
            # Use email as user_id
            user_id = request.email
            
            # Check if user already has a connection
            if self.check_user_connection(user_id):
                raise Exception(f"User {request.email} already has a connected account")
            
            # Get Gmail auth config
            auth_config = self.get_gmail_auth_config()
            if not auth_config:
                raise Exception("No Gmail auth configuration found. Please set up Gmail integration first.")
            
            callback_url = request.callback_url or DEFAULT_CALLBACK_URL
            
            # Create connection link
            connection_request = self.composio.connected_accounts.link(
                user_id=user_id,
                auth_config_id=auth_config.id,
                callback_url=callback_url
            )
            
            return SignInResponse(
                connection_url=connection_request.redirect_url,
                connection_id=connection_request.id,
                user_id=user_id
            )
        except Exception as e:
            raise Exception(f"Failed to create sign-in link: {str(e)}")
    
    def get_user_connection_status(self, email: str) -> UserConnectionStatus:
        """Get user connection status."""
        try:
            user_id = email
            is_connected = self.check_user_connection(user_id)
            
            connection_id = None
            if is_connected:
                connections = self.composio.connected_accounts.list(entity_id=user_id)
                connection_id = connections[0].id if connections else None
            
            return UserConnectionStatus(
                user_id=user_id,
                email=email,
                is_connected=is_connected,
                connection_id=connection_id
            )
        except Exception as e:
            raise Exception(f"Failed to get user connection status: {str(e)}")