# OpenStack Topology Explorer

A production-oriented web application that connects to an existing OpenStack cloud and produces a clean, easy-to-understand, hierarchical network topology across multiple OpenStack projects.

**Read-only** - This application never modifies OpenStack resources.

## Features

- **Single Traffic Topology**: One operational view from VM/network toward external connectivity
- **Network Containers**: Groups VMs into compact network/subnet zones
- **Multi-Project Support**: Select one project while retaining only relevant shared/external dependencies
- **Multi-NIC Appliances**: Shows one OpenStack VM with every real Neutron-port connection
- **Readability at Scale**: Deterministic VM grids, automatic left-to-right ELK layout, and orthogonal edges
- **Internet Path Discovery**: Highlights the logical OpenStack path from a selected VM

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        OpenStack Cloud                           │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Keystone │  │  Nova    │  │ Neutron   │  │          │       │
│  │(Identity)│  │(Compute) │  │(Network)  │  │          │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────────┘       │
│       │             │             │                             │
└───────┼─────────────┼─────────────┼─────────────────────────────┘
        │             │             │
        ▼             ▼             ▼
┌───────────────────────────────────────────────────────────────┐
│                    OpenStack SDK                                │
└───────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────┐
│                   Backend (FastAPI)                             │
│                                                                │
│  ┌────────────┐  ┌────────────┐  ┌─────────────────────────┐ │
│  │ Collectors │  │ Normalizer │  │ Classification Engine     │ │
│  │ - Identity │  │            │  │ - Device detection       │ │
│  │ - Compute  │  │            │  │ - Interface classification│ │
│  │ - Network  │  │            │  │ - Explicit VM roles      │ │
│  └────────────┘  └────────────┘  └─────────────────────────┘ │
│                                                                │
│  ┌────────────┐  ┌────────────┐  ┌─────────────────────────┐ │
│  │ Relationship│  │ Path Engine│  │ Sync Service            │ │
│  │ Engine     │  │            │  │ - Background refresh     │ │
│  │            │  │            │  │ - Error handling         │ │
│  └────────────┘  └────────────┘  └─────────────────────────┘ │
└───────────────────────────────────────────────────────────────┘
                                │
                                ▼ REST API
┌───────────────────────────────────────────────────────────────┐
│                   Frontend (React)                             │
│                                                                │
│  ┌────────────┐  ┌────────────┐  ┌─────────────────────────┐ │
│  │ Topology   │  │ Filters     │  │ Details Drawer          │ │
│  │ Canvas     │  │ - Projects  │  │ - Node information      │ │
│  │ (ReactFlow)│  │ - Resources │  │ - Internet path        │ │
│  │            │  │ - Status    │  │ - Connections          │ │
│  └────────────┘  └────────────┘  └─────────────────────────┘ │
└───────────────────────────────────────────────────────────────┘
```

## Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd openstack-topology-explorer

# Copy environment file
cp .env.example .env

# Start in demo mode (no OpenStack required)
# Docker Compose v2:
DEMO_MODE=true docker compose up -d --build
# Or the Compose v1 command installed on older Ubuntu hosts:
DEMO_MODE=true docker-compose up -d --build

# Access the application
open http://localhost:5173
```

### Option 2: Development Mode

**Backend:**

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp ../.env.example .env

# Run the server
uvicorn app.main:app --reload --port 8000
```

**Frontend:**

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

## Configuration

### OpenStack Authentication

**Option 1: Using clouds.yaml (Recommended)**

For Docker, copy the example to the already-mounted `config` directory:

```bash
cp clouds.yaml.example config/clouds.yaml
```

Then edit `config/clouds.yaml`:

```yaml
clouds:
  mycloud:
    auth:
      auth_url: https://keystone.example.com/v3
      username: topology-reader
      password: YOUR_PASSWORD
      project_name: admin
      user_domain_name: Default
      project_domain_name: Default
    region_name: RegionOne
    interface: internal
    identity_api_version: 3
```

Set the cloud name in `.env`:
```bash
OS_CLOUD=mycloud
CLOUDS_YAML_PATH=/app/config/clouds.yaml
```

**Option 2: Environment Variables**

```bash
OS_AUTH_URL=https://keystone.example.com/v3
OS_USERNAME=topology-reader
OS_PASSWORD=YOUR_PASSWORD
OS_PROJECT_NAME=admin
```

### OpenStack Service Account Requirements

The application requires a read-only service account with the following roles:

- **Keystone**: `reader` on all projects
- **Nova**: `reader` on all projects (for server listing)
- **Neutron**: `reader` on all projects (for networks, ports, routers)

Example Role Assignment:

```bash
# Create read-only project
openstack project create topology-reader

# Grant reader role to user
openstack role add --project topology-reader --user topology-reader reader
```

### Device Classification

Copy and customize the classification configuration:

```bash
cp config/classification.yaml.example config/classification.yaml
```

Firewall classification is explicit by design. A firewall-looking VM name such
as `PAN01` or `FW01` remains a regular VM unless one of these is configured:

1. Server metadata (`device_role=firewall`)
2. An OpenStack tag (`device_role=firewall`)

Name patterns remain available for non-firewall presentation roles, but never
create firewall or egress relationships.

Example metadata for firewall classification:

```bash
# On server metadata
openstack server set --property device_role=firewall --property device_vendor="Palo Alto" my-firewall-vm
```

Only appliances represented by Nova servers and Neutron ports appear. Physical
firewalls, routers, switches, external HA groups, and manually invented
datacenter links are intentionally outside the topology scope.

### Inventory cache (PostgreSQL)

Docker Compose starts PostgreSQL and stores normalized topology snapshots in the
`topology-postgres-data` volume. Each snapshot records `discovered_at` and
`last_seen_at`. This cache is non-authoritative: OpenStack remains the source of
truth, and the backend keeps the last valid snapshot available if a later
collector or the database is temporarily unavailable.

Set the same strong password in `POSTGRES_PASSWORD` and `DATABASE_URL` in
`.env`. For backend-only development, SQLite remains available by setting
`DATABASE_URL=sqlite:///./topology.db`.

## API Endpoints

### Topology

```
GET /api/v1/topology
GET /api/v1/topology/full
GET /api/v1/topology/summary
POST /api/v1/topology/refresh
```

### Projects

```
GET /api/v1/projects
GET /api/v1/projects/{project_id}
```

### Nodes

```
GET /api/v1/nodes/{node_id}
GET /api/v1/nodes/{node_id}/connections
GET /api/v1/nodes/{node_id}/ports
```

### Internet Path

```
GET /api/v1/path/{server_id}/internet
GET /api/v1/path/{server_id}/paths
```

### Sync Status

```
GET /api/v1/sync/status
POST /api/v1/sync/refresh
GET /api/v1/health
GET /api/v1/cloud/summary
GET /api/v1/search?q=10.0.30.15
GET /api/v1/servers/{server_id}
GET /api/v1/networks/{network_id}
GET /api/v1/routers/{router_id}
POST /api/v1/discovery/refresh
```

## Demo Mode

Enable demo mode to test without an OpenStack cloud:

```bash
DEMO_MODE=true docker compose up
```

Demo topology includes:
- 1 Project (NOC)
- 2 explicitly classified OpenStack appliance VMs (PAN01, PAN02)
- 1 External network (NOC-WAN)
- 3 Internal VLANs (VLAN10-AV, VLAN20-PAM, VLAN30-Monitor)
- 8 Servers (AV01, AV02, PAM01, PAM02, MON01, MON02, MON03)

## Topology Visualization

### Node Types

| Role | Description | Icon |
|------|-------------|------|
| VM | Virtual machine | 🖥️ |
| Firewall VM | Explicitly classified Nova server | compact rose-accent card |
| Router | Neutron router | 🔀 |
| Network | Neutron network and subnet container | grouped zone |
| Internet | Internet endpoint | ☁️ |

### Edge Types

| Relationship | Description | Style |
|--------------|-------------|-------|
| attached_to | Server connected to network | Solid |
| router_interface | Router interface | Solid |
| external_gateway | Router to external network | Solid |
| internet_uplink | External network to Internet | Dashed |

### Layout

The UI automatically uses one left-to-right Traffic Topology. ELK applies a
layered layout with orthogonal routing; there is no operator-facing layout or
view-mode selector.

## Troubleshooting

### Common Issues

**0. `KeyError: 'ContainerConfig'` while recreating a container**

This error comes from the obsolete Python-based Docker Compose v1
(`docker-compose` 1.29.2), not from the backend or frontend build. Install the
Compose v2 plugin and recreate the containers without deleting volumes:

```bash
sudo apt-get update
sudo apt-get install -y docker-compose-plugin
sudo docker compose version
sudo docker compose down --remove-orphans
sudo docker compose up -d --build
```

If the host distribution does not provide the v2 plugin yet, remove only this
project's stale containers before retrying with Compose v1:

```bash
sudo docker-compose down --remove-orphans
sudo docker rm -f topology-backend topology-frontend topology-postgres 2>/dev/null || true
sudo docker-compose up -d --build
```

Do not add `-v` to `down`; that option also removes named volumes.

**1. "No topology available" error**

```bash
# Check if OpenStack is reachable
curl -k https://keystone.example.com/v3

# Verify credentials
export OS_AUTH_URL=https://keystone.example.com/v3
export OS_USERNAME=topology-reader
export OS_PASSWORD=YOUR_PASSWORD
openstack token issue
```

**2. "Connection timeout" error**

Increase timeout in `.env`:
```bash
OPENSTACK_TIMEOUT=60
REQUEST_TIMEOUT=120
```

**3. TLS certificate errors**

Disable TLS verification (not recommended for production):
```bash
TLS_VERIFY=false
```

**4. Missing projects/networks**

Ensure the service account has `reader` role on all required projects:
```bash
openstack role assignment list --user topology-reader
```

### Logs

Backend logs:
```bash
docker compose logs -f backend
```

Frontend logs:
```bash
docker compose logs -f frontend
```

## Development

### Running Tests

```bash
cd backend
pip install pytest pytest-asyncio
pytest app/tests/ -v
```

### Project Structure

```
openstack-topology-explorer/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI endpoints
│   │   ├── openstack/     # OpenStack collectors
│   │   ├── topology/      # Topology engines
│   │   ├── repositories/  # PostgreSQL/SQLite snapshot cache
│   │   ├── schemas/      # Pydantic models
│   │   ├── services/      # Business logic
│   │   └── main.py        # Application entry
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── api/           # API client
│   │   ├── components/    # React components
│   │   ├── topology/      # Topology visualization
│   │   └── types/         # TypeScript types
│   ├── package.json
│   └── Dockerfile
│
├── config/
│   └── classification.yaml.example
│
├── docker-compose.yml
├── .env.example
├── clouds.yaml.example
└── README.md
```

## Security

- **Read-only**: The application never modifies OpenStack resources
- **Credentials**: Never exposed to frontend or logged
- **TLS**: Enabled by default
- **CORS**: Restricted to configured origins
- **No mutation APIs**: No POST/PUT/DELETE to OpenStack

## License

MIT License
