# UnboxEd web app image (build from the repo root: docker build -f apps/web/Dockerfile .)
FROM node:22-alpine AS build
WORKDIR /repo
COPY apps/web/package.json apps/web/package-lock.json apps/web/
RUN npm --prefix apps/web ci
COPY packages packages
COPY apps/web apps/web
ARG NEXT_PUBLIC_SITE_URL=http://localhost:5195
ENV NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL NEXT_TELEMETRY_DISABLED=1
RUN npm --prefix apps/web run build

FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production PORT=3010 HOSTNAME=0.0.0.0 NEXT_TELEMETRY_DISABLED=1
COPY --from=build /repo/apps/web/.next/standalone ./
COPY --from=build /repo/apps/web/.next/static ./.next/static
COPY --from=build /repo/apps/web/public ./public
USER node
EXPOSE 3010
CMD ["node", "server.js"]
