"""
Google Drive integration for uploading CMA reports as editable Google Docs
Saves documents to user's own Google Drive account via OAuth
"""

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from typing import Optional, Dict, List
import streamlit as st


class GoogleDriveExporter:
    """Upload HTML reports to user's Google Drive as editable Google Docs"""

    def __init__(self, access_token: str):
        """
        Initialize with user's OAuth access token

        Args:
            access_token: User's Google OAuth2 access token from streamlit-oauth
        """
        # Create credentials from access token
        self.credentials = Credentials(token=access_token)
        self.service = build('drive', 'v3', credentials=self.credentials)

    def upload_html_as_doc(self, html_path: str, doc_title: str) -> Dict[str, str]:
        """
        Upload HTML file to Google Drive, converted to Google Doc

        Args:
            html_path: Path to HTML file to upload
            doc_title: Title for the Google Doc

        Returns:
            Dictionary with 'id', 'web_view_link', and 'name' of created document

        Raises:
            HttpError: If upload fails
        """
        try:
            # Metadata for the new Google Doc
            file_metadata = {
                'name': doc_title,
                'mimeType': 'application/vnd.google-apps.document'  # Convert to Google Doc
            }

            # Prepare file upload
            media = MediaFileUpload(
                html_path,
                mimetype='text/html',
                resumable=True
            )

            # Upload file to user's Drive
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink, createdTime'
            ).execute()

            return {
                'id': file.get('id'),
                'name': file.get('name'),
                'web_view_link': file.get('webViewLink'),
                'created_time': file.get('createdTime')
            }

        except HttpError as error:
            raise Exception(f"Failed to upload to Google Drive: {error}")

    def list_recent_docs(self, limit: int = 10) -> List[Dict]:
        """
        List user's recent Google Docs (optional feature for future use)

        Args:
            limit: Maximum number of documents to return

        Returns:
            List of dictionaries with doc metadata
        """
        try:
            results = self.service.files().list(
                q="mimeType='application/vnd.google-apps.document' and trashed=false",
                pageSize=limit,
                orderBy='modifiedTime desc',
                fields="files(id, name, webViewLink, modifiedTime)"
            ).execute()

            return results.get('files', [])

        except HttpError as error:
            st.warning(f"Could not list recent documents: {error}")
            return []

    def check_quota(self) -> Optional[Dict]:
        """
        Check user's Google Drive storage quota (optional feature)

        Returns:
            Dictionary with 'usage', 'limit', and 'usage_percent'
        """
        try:
            about = self.service.about().get(fields='storageQuota').execute()
            quota = about.get('storageQuota', {})

            usage = int(quota.get('usage', 0))
            limit = int(quota.get('limit', 0))

            if limit > 0:
                usage_percent = (usage / limit) * 100
            else:
                usage_percent = 0

            return {
                'usage': usage,
                'limit': limit,
                'usage_percent': usage_percent
            }

        except HttpError:
            return None
