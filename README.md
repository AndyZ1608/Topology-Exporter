# OpenStack Topology Explorer

A production-oriented web application that connects to an existing OpenStack cloud and produces a clean, easy-to-understand, hierarchical network topology across multiple OpenStack projects.

**Read-only** - This application never modifies OpenStack resources.

## Features

- **Traffic-Path-Centric Topology**: Visualizes the path from VM to Internet
- **Multi-Project Support**: See topology across all OpenStack projects
- **Firewall Detection**: Automatically identifies firewalls (Palo Alto, Fortinet, Check Point, etc.)
- **HA Group Support**: Groups clustered firewalls together
- **Trunk Support**: Visualizes trunk connections
- **Internet Path Discovery**: Shows the logical path from any VM to the Internet
- **Inferred vs Confirmed**: Distinguishes between OpenStack-confirmed relationships and inferred topology

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
│  │ - Network  │  │            │  │ - HA grouping            │ │
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
DEMO_MODE=true docker-compose up -d

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

Create or edit `~/.config/openstack/clouds.yaml`:

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

The classifier uses these priorities:
1. Manual classification (stored in database)
2. Server metadata (`device_role`, `device_vendor`, `device_group`)
3. OpenStack tags
4. `classification.yaml` patterns
5. Regex pattern matching on server names
6. Default: `vm`

Example metadata for firewall classification:

```bash
# On server metadata
openstack server set --property device_role=firewall --property device_vendor="Palo Alto" --property device_group=PAN-HA my-firewall-vm
```

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
```

## Demo Mode

Enable demo mode to test without an OpenStack cloud:

```bash
DEMO_MODE=true docker-compose up
```

Demo topology includes:
- 1 Project (NOC)
- 2 Firewalls (PAN01, PAN02) in HA group
- 1 External network (NOC-WAN)
- 3 Internal VLANs (VLAN10-AV, VLAN20-PAM, VLAN30-Monitor)
- 8 Servers (AV01, AV02, PAM01, PAM02, MON01, MON02, MON03)

## Topology Visualization

### Node Types

| Role | Description | Icon |
|------|-------------|------|
| VM | Virtual machine | 🖥️ |
| Firewall | Firewall appliance | 🔥 |
| Router | Neutron router | 🔀 |
| Network | Neutron network | 🌐 |
| HA Group | Firewall HA cluster | 🔗 |
| Internet | Internet endpoint | ☁️ |

### Edge Types

| Relationship | Description | Style |
|--------------|-------------|-------|
| attached_to | Server connected to network | Solid |
| router_interface | Router interface | Solid |
| external_gateway | Router to external network | Solid |
| internet_uplink | External network to Internet | Dashed |
| egress_via | Inferred firewall path | Dashed |

### Layout Directions

- **Top to Bottom** (default): VM → Network → Firewall → Internet
- **Bottom to Top**: Inverse direction
- **Left to Right**: Horizontal layout
- **Right to Left**: Inverse horizontal

## Troubleshooting

### Common Issues

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
docker-compose logs -f backend
```

Frontend logs:
```bash
docker-compose logs -f frontend
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
