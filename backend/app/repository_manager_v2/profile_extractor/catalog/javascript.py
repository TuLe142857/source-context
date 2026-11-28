"""JavaScript and TypeScript catalog defining frameworks, libraries, manifests, and entrypoints."""

from typing import Any

JAVASCRIPT_CATALOG: dict[str, Any] = {
    "language": "javascript",
    "package_managers": {
        "pnpm-lock.yaml": "pnpm",
        "yarn.lock": "yarn",
        "bun.lockb": "bun",
        "package-lock.json": "npm",
    },
    "frameworks": {
        # Frontend Frameworks
        "react": {"name": "React", "type": "frontend_app"},
        "react-dom": {"name": "React", "type": "frontend_app"},
        "vue": {"name": "Vue.js", "type": "frontend_app"},
        "svelte": {"name": "Svelte", "type": "frontend_app"},
        "@sveltejs/kit": {"name": "SvelteKit", "type": "frontend_app"},
        "next": {"name": "Next.js", "type": "frontend_app"},
        "nuxt": {"name": "Nuxt.js", "type": "frontend_app"},
        "astro": {"name": "Astro", "type": "frontend_app"},
        "@remix-run/react": {"name": "Remix", "type": "frontend_app"},
        "vite": {"name": "Vite", "type": "frontend_app"},
        "tailwindcss": {"name": "Tailwind CSS", "type": None},
        "zustand": {"name": "Zustand", "type": None},
        "@reduxjs/toolkit": {"name": "Redux Toolkit", "type": None},
        # Backend Frameworks
        "express": {"name": "Express", "type": "backend_service"},
        "@nestjs/core": {"name": "NestJS", "type": "backend_service"},
        "fastify": {"name": "Fastify", "type": "backend_service"},
        "koa": {"name": "Koa", "type": "backend_service"},
        "hono": {"name": "Hono", "type": "backend_service"},
        # Database & ORM
        "prisma": {"name": "Prisma", "type": None},
        "@prisma/client": {"name": "Prisma", "type": None},
        "typeorm": {"name": "TypeORM", "type": None},
        "drizzle-orm": {"name": "Drizzle ORM", "type": None},
        "mongoose": {"name": "Mongoose", "type": None},
        # Testing
        "vitest": {"name": "Vitest", "type": None},
        "jest": {"name": "Jest", "type": None},
        "playwright": {"name": "Playwright", "type": None},
        "cypress": {"name": "Cypress", "type": None},
    },
    "entrypoint_files": [
        "src/main.tsx",
        "src/main.ts",
        "src/App.tsx",
        "src/App.vue",
        "src/index.tsx",
        "src/index.ts",
        "src/index.js",
        "index.html",
        "server.ts",
        "server.js",
        "app.ts",
        "app.js",
        "pages/_app.tsx",
        "app/layout.tsx",
    ],
    "script_keys": [
        "dev",
        "start",
        "build",
        "serve",
    ],
}
