# OpenStack Topology Explorer

OpenStack Topology Explorer is a lightweight web tool for visualizing OpenStack project network topology. It discovers VMs, networks, subnets, routers, and IP information and presents a simple traffic-oriented view:

```text
VM → Network → Router / virtual network appliance → Internet
```

It helps operators quickly understand how workloads in a selected project are connected.

## Features

- Discover OpenStack projects
- Display all VMs in a selected project
- Show VM IP addresses, networks, and subnets
- Show Neutron routers and gateway IPs
- Show WAN/external IPs and Internet connectivity
- Support multi-NIC VMs and Neutron trunks
- Use read-only OpenStack access

## Requirements

- Ubuntu 22.04 or 24.04
- Docker
- Docker Compose v2
- Network access to the OpenStack internal APIs
- An OpenStack read-only account

Required API access:

```text
5000  Keystone
8774  Nova
9696  Neutron
9292  Glance
8776  Cinder
```

Topology discovery mainly depends on Keystone, Nova, and Neutron.

## Configuration

Clone the repository and create the environment file:

```bash
git clone <repository-url>
cd Topology-Exporter
cp .env.example .env
nano .env
```

Configure `.env` for OpenStack:

```env
DEMO_MODE=false

OS_AUTH_URL=http://10.1.114.11:5000/v3
OS_USERNAME=topology-reader
OS_PASSWORD=CHANGE_ME
OS_USER_DOMAIN_NAME=Default

OS_REGION_NAME=RegionOne
OS_INTERFACE=internal
OS_IDENTITY_API_VERSION=3

TOPOLOGY_DOMAIN_NAME=MBFS
```

Also change `POSTGRES_PASSWORD` and use the same password in `DATABASE_URL`.

Do not set `OS_PROJECT_NAME` or `OS_SYSTEM_SCOPE`. The backend discovers projects from the configured domain and creates project-scoped OpenStack connections automatically.

The application is designed to use a read-only OpenStack account. Never commit `.env` or OpenStack credentials to Git.

## Run with Docker Compose

Build and start all services:

```bash
sudo docker compose up -d --build
```

Check that `postgres`, `backend`, and `frontend` are running:

```bash
sudo docker compose ps
```

## Access the Web UI

Open the following address in your browser:

```text
http://<TOPOLOGY-SERVER-IP>:5173
```

The backend API is exposed on port `8000`.

## Useful Commands

```bash
# Check containers
sudo docker compose ps

# View all logs
sudo docker compose logs -f

# View backend logs
sudo docker compose logs -f backend

# Rebuild after code changes
sudo docker compose up -d --build
```

## Stop / Restart

```bash
# Stop the application
sudo docker compose down

# Restart running services
sudo docker compose restart

# Full rebuild
sudo docker compose down
sudo docker compose up -d --build
```

## Troubleshooting

### Cannot connect to OpenStack

Check connectivity from the topology server:

```bash
nc -zvw3 <OPENSTACK_API_IP> 5000
nc -zvw3 <OPENSTACK_API_IP> 8774
nc -zvw3 <OPENSTACK_API_IP> 9696
```

### OpenStack returns 403

Verify that the configured user has the `reader` role on the required OpenStack projects/domain. Do not grant `admin` for this application.

### No topology data

Check the backend logs:

```bash
sudo docker compose logs -f backend
```

Confirm that `DEMO_MODE=false` and the OpenStack credentials in `.env` are correct.

### Docker Compose command not found

This project requires Docker Compose v2:

```bash
docker compose version
```
