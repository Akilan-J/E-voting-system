# 🗳️ E-Voting System
### Secure, Privacy-Preserving Electronic Voting with Homomorphic Encryption

![Docker](https://img.shields.io/badge/docker-ready-blue) ![Python](https://img.shields.io/badge/python-3.11-blue) ![React](https://img.shields.io/badge/react-18-blue)

---

## 🚀 Quick Start

### Prerequisites
- Docker Desktop installed and running
- 8GB RAM minimum
- Ports free: 3000, 8000, 5432, 8545

### Setup & Run

```bash
# Clone and navigate
cd E-voting-system

# Start all services
docker-compose up -d

# Wait 30 seconds for database initialization

# Verify all containers running
docker-compose ps
```

**Access:** http://localhost:3000

---

## ⚡ Run Your First Election (2 minutes)

### Testing Tab - Setup Phase
1. **🔧 Setup Trustees** - Click & wait for success
2. **🗳️ Generate 100 Mock Votes** - Click & wait 20 seconds (encryption takes time)
3. **🔢 Generate 100 Mock Ballots** - Click & wait
4. **📍 Tally Ballots** - Click to aggregate votes
5. **✨ Start Tallying Process** - Click to initialize decryption

### Trustees Tab - Decryption Phase
6. Click **🔓 Decrypt** for 3 different trustees (any 3)
   - Watch progress: 1/3 → 2/3 → 3/3 ✅

### Testing Tab - Finalization
7. **⛓️ Finalize Tally on Blockchain** - Click to complete

### Results Tab - View Winner
8. See vote distribution, winner, and blockchain verification! 🏆

---

## 🏗️ System Architecture

```
┌─────────────┐      ┌─────────────┐      ┌──────────────┐
│   React     │─────▶│   FastAPI   │─────▶│  PostgreSQL  │
│  Frontend   │      │   Backend   │      │   Database   │
│  :3000      │      │   :8000     │      │   :5432      │
└─────────────┘      └─────────────┘      └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │   Ganache    │
                     │  Blockchain  │
                     │   :8545      │
                     └──────────────┘
```

**Components:**
- **Frontend** - React 18 with modern UI/UX
- **Backend** - FastAPI with Paillier encryption
- **Database** - PostgreSQL 15 for vote storage
- **Blockchain** - Ganache for result immutability

---

## 🔐 Security Features

- **Homomorphic Encryption** - Votes remain encrypted during tallying (Paillier 2048-bit)
- **Threshold Cryptography** - 3-of-5 trustees required (Shamir's Secret Sharing)
- **Zero-Knowledge Proofs** - Verifiable decryption without revealing private keys
- **Blockchain Verification** - Immutable result publication
- **Merkle Trees** - Ballot integrity verification
- **Audit Logging** - Complete operation tracking

---

## 📡 API Reference

**Base URL:** http://localhost:8000/api

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/tally/start` | POST | Start tallying process |
| `/tally/partial-decrypt/{trustee_id}` | POST | Trustee decryption |
| `/tally/finalize` | POST | Compute final results |
| `/results/{election_id}` | GET | View results |
| `/mock/generate-votes?count=100` | POST | Generate test votes |

**Full API Docs:** http://localhost:8000/docs

---

## 🛠️ Development

### Environment Setup

```bash
# Frontend development
cd frontend
npm install
npm start

# Backend development
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Database migrations
cd backend
alembic upgrade head
```

### Useful Commands

```bash
# View logs
docker-compose logs -f

# Restart services
docker-compose restart backend
docker-compose restart frontend

# Reset database
curl -X POST "http://localhost:8000/api/mock/reset-database?confirm=true"

# Stop all
docker-compose down

# Full cleanup (removes volumes)
docker-compose down -v
```

---

## 🐛 Troubleshooting

**"Generate Votes" shows "Action Failed"**
- Normal! Wait 20 seconds for encryption to complete
- Success message appears after processing

**"Finalization Failed: Key Mismatch"**
- Reset database and start fresh workflow
- Don't repeat any step - each button clicked only once

**"Decrypt" button disabled**
- Complete Testing tab steps 1-5 first

**No results showing**
- Ensure 3 trustees decrypted
- Click "Finalize Tally" in Testing tab

**Containers won't start**
```bash
docker-compose down -v
docker-compose up -d --build
```

**Frontend won't compile**
```bash
docker-compose restart frontend
docker logs evoting_frontend -f
```

---

## 📂 Project Structure

```
E-voting-system/
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   │   ├── TestingPanel.jsx
│   │   │   ├── TrusteePanel.jsx
│   │   │   └── ResultsDashboard.jsx
│   │   ├── services/        # API client
│   │   └── App.js
│   └── package.json
├── backend/
│   ├── app/
│   │   ├── routers/         # API endpoints
│   │   ├── services/        # Business logic
│   │   │   ├── encryption.py
│   │   │   ├── tallying.py
│   │   │   └── threshold_crypto.py
│   │   ├── models/          # Database models
│   │   └── main.py
│   └── requirements.txt
├── docker-compose.yml
└── README.md
```

---

## 🔬 Technical Details

### Cryptographic Implementation

**Encryption:** Paillier homomorphic cryptosystem
```python
# Votes are encrypted: E(v)
# Tallying: E(v1) × E(v2) × ... = E(v1 + v2 + ...)
# Decrypt once to get total
```

**Threshold Scheme:** 3-of-5 Shamir's Secret Sharing
```python
# Private key split into 5 shares
# Any 3 shares can reconstruct key
# No single trustee can decrypt alone
```

**Zero-Knowledge Proofs:** Trustees prove correct decryption without revealing shares

### Database Schema

- **elections** - Election metadata
- **encrypted_votes** - Homomorphically encrypted votes
- **trustees** - Trustee info and key shares
- **partial_decryptions** - Individual trustee decryptions
- **tallying_sessions** - Tallying state tracking
- **results** - Final decrypted results

---

## 🎯 Key Workflow

```
1. Setup → 2. Vote Encryption → 3. Aggregation → 4. Threshold Decryption → 5. Result Publication

[Trustees Setup]  →  [100 Votes Generated]  →  [Homomorphic Tally]
                                                         ↓
[Blockchain Publish]  ←  [Final Results]  ←  [3/5 Trustees Decrypt]
```

---

## ⚠️ Important Notes

- **Demo System** - Not production-ready
- Each workflow step should be clicked **only once**
- Vote generation takes **~20 seconds** due to encryption
- Need **exactly 3 trustees** to decrypt (can't use 2 or 4)
- Always reset database between test runs for clean state

---

## 📊 Performance

- Vote encryption: ~200ms per vote
- 100 votes: ~20 seconds
- Homomorphic aggregation: <2 seconds
- Partial decryption per trustee: <1 second
- Finalization: <3 seconds

---

## 🚧 Production Considerations

For real elections, implement:
- ✅ Real cryptographic key management (HSM)
- ✅ Trustee authentication & authorization
- ✅ Production blockchain (Ethereum mainnet/L2)
- ✅ Voter identity verification
- ✅ Rate limiting & DDoS protection
- ✅ Audit logging to external system
- ✅ Backup & disaster recovery
- ✅ Security penetration testing

---

## 📚 Additional Resources

- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health
- **Paillier Cryptosystem:** [Wikipedia](https://en.wikipedia.org/wiki/Paillier_cryptosystem)
- **Shamir's Secret Sharing:** [Wikipedia](https://en.wikipedia.org/wiki/Shamir%27s_Secret_Sharing)

---

## 🤝 Contributing

This is a demonstration project for educational purposes.

---

## 🔀 GitHub Workflow

This guide outlines the Git workflow for contributing to this project.

### 1. Sync with the main branch
Before starting any new work, ensure your main branch is up-to-date with the remote repository.

```bash
git switch main
git pull origin main
```

### 2. Create or Switch to a Feature Branch
Create a new branch for your feature or bug fix. This isolates your changes from the main branch.

```bash
# Switch to your existing feature branch
git switch <your-feature-branch>

# Or create a new feature branch
git switch -c <your-feature-branch>
```

### 3. Sync your Feature Branch with main
Periodically, you should update your feature branch with the latest changes from main.

```bash
git pull origin main
```

This helps to avoid large merge conflicts later.

### 4. Develop and Commit
Make your code changes, then stage and commit them.

```bash
# Create or modify files
touch new_file.py

# Stage your changes
git add .

# Commit your changes with a descriptive message
git commit -m "Your descriptive commit message"
```

### 5. Push your Feature Branch
Push your feature branch to the remote repository. This backs up your work and prepares it for a pull request.

```bash
git push origin <your-feature-branch>
```

### 6. Merge your changes
Once your feature is complete and reviewed, merge it into the main branch.

```bash
# Switch to the main branch
git switch main
git pull origin main

# Merge your feature branch
git merge <your-feature-branch>
```

If there are merge conflicts, resolve them, and then commit the changes.

```bash
# After resolving conflicts
git add .
git commit
```

### 7. Push the Merged main Branch
Finally, push the updated main branch to the remote repository.

```bash
git push origin main
```

### 8. (Optional) Continue Working on Your Feature Branch
If you want to continue working on your feature branch after the merge, switch back to it and sync with the updated main.

```bash
# Switch back to your feature branch
git switch <your-feature-branch>

# Sync with the merged main branch
git pull origin main
```

### Contributing Guidelines
Please follow the workflow above when contributing to this project. Always ensure your feature branch is up-to-date with main before submitting a pull request.

---

**Status:** ✅ Fully Functional | **Version:** 1.0.0 | **Last Updated:** January 2026