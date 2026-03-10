# Vercel Deployment Setup Guide

Step-by-step instructions to activate the Vercel deploy workflow for the E-Voting System frontend.

---

## Prerequisites

- A [Vercel account](https://vercel.com/signup) (free tier works)
- Admin/write access to the GitHub repository
- Node.js installed locally (for the Vercel CLI)

---

## Step 1 — Install Vercel CLI

```bash
npm install -g vercel
```

---

## Step 2 — Link the Project

Run this from the project root:

```bash
cd E-voting-system
vercel link
```

You will be prompted to:
1. Log in to Vercel (opens browser)
2. Select your Vercel scope (personal account or team)
3. Link to an existing project or create a new one — choose **Create a new project**
4. Confirm the project name (e.g., `e-voting-system`)

This creates a `.vercel/` directory locally with a `project.json` file. **Do not commit this** — it is already in `.gitignore`.

---

## Step 3 — Get Your IDs

Open the generated file:

```bash
cat .vercel/project.json
```

You will see something like:

```json
{
  "projectId": "prj_xxxxxxxxxxxxxxxxxxxx",
  "orgId": "team_xxxxxxxxxxxxxxxxxxxx"
}
```

Copy both values — you'll need them in the next step.

---

## Step 4 — Create a Vercel Token

1. Go to [vercel.com/account/tokens](https://vercel.com/account/tokens)
2. Click **Create Token**
3. Name it (e.g., `github-actions-deploy`)
4. Set scope to your account or team
5. Copy the token — you won't see it again

---

## Step 5 — Add GitHub Secrets

Go to your repository on GitHub:

**Settings → Secrets and variables → Actions → New repository secret**

Add these three secrets:

| Secret Name | Value |
|-------------|-------|
| `VERCEL_TOKEN` | The token from Step 4 |
| `VERCEL_ORG_ID` | The `orgId` from `.vercel/project.json` |
| `VERCEL_PROJECT_ID` | The `projectId` from `.vercel/project.json` |

---

## Step 6 — Push and Deploy

Once the secrets are set, the deploy workflow triggers automatically on every push to `all` or `main`:

```bash
git add .
git commit -m "Enable Vercel CI/CD"
git push origin all
```

Check the workflow run at:  
`https://github.com/niranjanagopinath/E-voting-system/actions`

The deploy job will:
1. Pull the Vercel project environment
2. Build the React frontend
3. Deploy to production
4. Verify the deployment URL

---

## Step 7 — Verify

After the workflow completes, your frontend will be live at:

```
https://<project-name>.vercel.app
```

You can also find the URL in:
- The GitHub Actions job summary
- The Vercel dashboard under your project

---

## Manual Deploy (Optional)

To deploy without GitHub Actions:

```bash
cd E-voting-system
vercel --prod
```

Or for a preview deploy (non-production):

```bash
vercel
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `Error: No project found` | Run `vercel link` again from the project root |
| `Error: Invalid token` | Regenerate the token at vercel.com/account/tokens and update the GitHub secret |
| Build fails | Check that `frontend/package.json` exists and `npm run build` works locally |
| 404 on page refresh | Verify `vercel.json` has the SPA rewrite rule (`/(.*) → /index.html`) |
| API calls fail | The backend is not hosted on Vercel — configure `REACT_APP_API_URL` to point to your backend host |

---

## Important Notes

- **Frontend only:** Vercel deploys the React SPA. The backend (FastAPI, PostgreSQL, Redis, Ganache) must be hosted separately.
- **Environment variables:** If the frontend needs to call a remote backend, add `REACT_APP_API_URL` in the Vercel dashboard under Project → Settings → Environment Variables.
- **Branch deploys:** Pushes to `all` and `main` trigger production deploys. PRs to these branches get preview URLs automatically (if Vercel GitHub integration is enabled).
- **`.vercel/` directory:** Created locally by `vercel link`. Already excluded via `.gitignore` — never commit it.
