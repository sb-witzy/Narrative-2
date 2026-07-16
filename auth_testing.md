# Auth Testing Playbook — Narrative.Rx

## MongoDB Verification
```
mongosh
use test_database
db.users.find().pretty()
db.users.findOne({role: "admin"}, {password_hash: 1})
db.narratives.find({user_id: "<uid>"}).count()
db.appeals.find({user_id: "<uid>"}).count()
```
- Admin user must exist with email `admin@dental.com`
- `password_hash` must begin with `$2b$` (bcrypt)
- Indexes: `users.email` unique, `narratives.user_id`, `visits.user_id`, `appeals.user_id`, `login_attempts.identifier`

## API smoke test
```
curl -c cookies.txt -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@dental.com","password":"admin123"}'

curl -b cookies.txt http://localhost:8001/api/auth/me
```
Login should set `access_token` + `refresh_token` cookies. `/me` should return the user object.

## Per-user isolation
- Register two users A and B.
- Generate a narrative as user A.
- Log in as user B; `GET /api/history` must return an empty list.
- Attempt `GET /api/history/{A_record_id}` as user B → 404.

## Appeal generation
```
NARR_ID=$(curl -sb cookies.txt -X POST http://localhost:8001/api/generate \
  -H "Content-Type: application/json" \
  -d '{"procedure_code":"D3330","tooth_number":"30","clinical_findings":"..."}' | jq -r .id)

curl -sb cookies.txt -X POST http://localhost:8001/api/appeals \
  -H "Content-Type: application/json" \
  -d "{\"narrative_id\":\"$NARR_ID\",\"denial_reason\":\"Not medically necessary\"}"
```

## Brute-force protection
- Send 5 login attempts with the wrong password → 6th attempt returns 429.
- Successful login within lockout is blocked.
