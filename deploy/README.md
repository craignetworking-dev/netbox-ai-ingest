# Layer 1 — Deployment

Goal: one command brings up a clean, reproducible NetBox you can log into.

## Prerequisites
- Docker + Docker Compose v2 — check with `docker compose version`
- ~4 GB free RAM

## Run
```bash
cd deploy
./bootstrap.sh
```
First boot runs migrations (~1-2 min). Then create an admin user:
```bash
cd .netbox-docker
docker compose exec netbox /opt/netbox/netbox/manage.py createsuperuser
```
Browse to http://localhost:8000 and log in.

## Reproducibility
`bootstrap.sh` defaults to upstream `release` so it just works the first time.
For a locked build, pin the exact version after first boot:
```bash
git -C .netbox-docker describe --tags        # e.g. 3.10.0-3.2.1
NETBOX_DOCKER_REF=3.10.0-3.2.1 ./bootstrap.sh
```
Record the ref you chose right here once you've picked one:

> Pinned ref: `5.0.1`

## Definition of done (this session)
- [ ] `./bootstrap.sh` brings the stack up with no errors
- [ ] NetBox loads at http://localhost:8000
- [ ] You can log in as the superuser you created
- [ ] Repo committed and pushed to a **public** GitHub repo

## Teardown
```bash
cd .netbox-docker && docker compose down       # keep data
cd .netbox-docker && docker compose down -v     # wipe volumes
```
