## 1. Backend GraphQL

- [x] 1.1 Add `ProfileUpdateResult` type with success, error, user fields
- [x] 1.2 Add `updateProfile` mutation (firstName, lastName, email - all optional)
- [x] 1.3 Validate email uniqueness within tenant if email is being changed
- [x] 1.4 Return updated user data on success

## 2. Frontend - Profile Section

- [x] 2.1 Add profile edit section to Settings page with first name, last name, email fields
- [x] 2.2 Pre-populate fields with current user data
- [x] 2.3 Add save button that calls updateProfile mutation
- [x] 2.4 Show success/error feedback
- [x] 2.5 Update cached user data after successful save

## 3. Translations

- [x] 3.1 Add profile section translations (en.json, de.json)

## 4. Testing

- [x] 4.1 Add backend test for profile update success
- [x] 4.2 Add backend test for email uniqueness validation
