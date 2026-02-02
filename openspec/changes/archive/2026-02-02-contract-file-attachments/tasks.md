## 1. Infrastructure Setup

- [x] 1.1 Add host-mounted uploads volume to docker-compose.yml (`./uploads:/app/media/uploads`)
- [x] 1.2 Add file upload settings to Django base settings (MAX_UPLOAD_SIZE, ALLOWED_ATTACHMENT_EXTENSIONS)

## 2. Backend Model

- [x] 2.1 Create ContractAttachment model with FileField, original_filename, file_size, content_type, uploaded_by
- [x] 2.2 Implement attachment_upload_path function for path structure `uploads/{tenant_id}/contracts/{contract_id}/{uuid}_{ext}`
- [x] 2.3 Override model delete() to remove file from storage
- [x] 2.4 Generate and run database migration

## 3. GraphQL Schema

- [x] 3.1 Create ContractAttachmentType with id, originalFilename, fileSize, contentType, downloadUrl, uploadedAt, uploadedByName
- [x] 3.2 Create UploadAttachmentInput (contractId, fileContent, filename, contentType, description)
- [x] 3.3 Create AttachmentResult type (attachment, success, error)
- [x] 3.4 Add attachments field to ContractType
- [x] 3.5 Implement uploadContractAttachment mutation with file validation
- [x] 3.6 Implement deleteContractAttachment mutation

## 4. Download Endpoint

- [x] 4.1 Create AttachmentDownloadView in apps/contracts/views.py
- [x] 4.2 Implement authentication check using get_current_user_from_request
- [x] 4.3 Implement tenant verification
- [x] 4.4 Return FileResponse with Content-Disposition header
- [x] 4.5 Add URL route at /api/attachments/{id}/download/

## 5. Frontend UI

- [x] 5.1 Add attachments field to CONTRACT_DETAIL_QUERY
- [x] 5.2 Add Attachment interface to TypeScript types
- [x] 5.3 Create UPLOAD_ATTACHMENT_MUTATION and DELETE_ATTACHMENT_MUTATION
- [x] 5.4 Add "Attachments" tab button to ContractDetail tabs
- [x] 5.5 Create AttachmentsTab component with file list table
- [x] 5.6 Implement file upload with FileReader and base64 encoding
- [x] 5.7 Implement download button (opens REST endpoint)
- [x] 5.8 Implement delete button with confirmation

## 6. Translations

- [x] 6.1 Add attachments section to en.json (title, noAttachments, uploadFile, uploading, filename, size, uploadedBy, uploadedAt, download, delete, confirmDelete)
- [x] 6.2 Add attachments section to de.json

## 7. Testing

- [x] 7.1 Add backend tests for upload mutation (success, invalid type, too large)
- [x] 7.2 Add backend tests for delete mutation (success, not found, wrong tenant)
- [x] 7.3 Add backend tests for download view (success, unauthorized, not found)
- [x] 7.4 Verify file is stored at correct path
- [x] 7.5 Verify file is deleted from storage when attachment is deleted
