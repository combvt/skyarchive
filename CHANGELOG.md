# CHANGELOG

## v0.1 - Initial release (21-Dec-2025)
### Added
- User registration endpoint
- User login endpoint
- JWT-based authentication

### Security
- Password hashing
- Token-based auth flow

### Infrastructure
- Database setup
- Auth-related tests


## v0.2 - Horizons integration (29-Dec-2025)
### Added
- Automatic location to coords conversion
- Grammar/token-based Horizons API data parser
- `GET /horizons/search` protected endpoint to fetch data about a specific astronomical object based on user location

### Changed
- Switched login authentication flow to form-based `OAuth2PasswordRequestForm` in order to be Swagger-friendly

### Notes
- `GET /horizons/search` can return 2 different response shapes (single/multi-match)
- Multi-match responses exclude `None` fields