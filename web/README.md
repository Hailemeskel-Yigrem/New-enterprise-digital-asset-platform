# VaultForge Web

Production frontend for the VaultForge enterprise digital asset platform.

## Stack

- Next.js 14 (App Router)
- React 18
- TypeScript
- Tailwind CSS
- TanStack Query
- React Hook Form + Zod

## Getting started

```bash
cp .env.example .env.local
npm install
npm run dev
```

Open `http://localhost:3000` in your browser. The API base URL defaults to `http://localhost:8000/api/v1`.

## Scripts

| Command         | Description              |
| --------------- | ------------------------ |
| `npm run dev`   | Start development server |
| `npm run build` | Production build         |
| `npm run start` | Start production server  |
| `npm run lint`  | Run ESLint               |
