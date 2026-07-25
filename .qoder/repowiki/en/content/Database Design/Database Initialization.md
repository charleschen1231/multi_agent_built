# Database Initialization

<cite>
**Referenced Files in This Document**
- [database/db_manager.py](file://database/db_manager.py)
- [database/models.py](file://database/models.py)
- [database/__init__.py](file://database/__init__.py)
- [web/app.py](file://web/app.py)
- [main_web.py](file://main_web.py)
- [web/pages/dashboard.py](file://web/pages/dashboard.py)
- [web/pages/data_manager.py](file://web/pages/data_manager.py)
- [web/pages/execution_flow.py](file://web/pages/execution_flow.py)
- [web/pages/training.py](file://web/pages/training.py)
- [configs/api_config.yaml](file://configs/api_config.yaml)
- [requirements.txt](file://requirements.txt)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)
10. [Appendices](#appendices)

## Introduction
This document explains how the application initializes and manages its database. It covers the database engine configuration, connection handling, schema creation, and the lifecycle of the database manager. It also documents how the database integrates with the web application and training/execution flows, and provides guidance for environment-specific setup, backup/restore, maintenance, monitoring, and security.

## Project Structure
The database layer consists of a single SQLite database managed by SQLAlchemy ORM. The database is initialized automatically when the application starts, and the database manager exposes CRUD APIs for datasets, system configurations, generated trajectories, execution records, and training jobs.

```mermaid
graph TB
subgraph "Application"
WEB_APP["web/app.py<br/>Creates AppState and DatabaseManager"]
MAIN_WEB["main_web.py<br/>Entry point for web UI"]
DASHBOARD["web/pages/dashboard.py"]
DATA_MGR["web/pages/data_manager.py"]
EXEC_FLOW["web/pages/execution_flow.py"]
TRAIN_PAGE["web/pages/training.py"]
end
subgraph "Database Layer"
DB_INIT["database/__init__.py<br/>Exports DatabaseManager and models"]
DB_MGR["database/db_manager.py<br/>Engine, sessions, tables"]
MODELS["database/models.py<br/>SQLAlchemy Declarative Base and tables"]
end
MAIN_WEB --> WEB_APP
WEB_APP --> DB_MGR
DASHBOARD --> DB_MGR
DATA_MGR --> DB_MGR
EXEC_FLOW --> DB_MGR
TRAIN_PAGE --> DB_MGR
DB_INIT --> DB_MGR
DB_MGR --> MODELS
```

**Diagram sources**
- [web/app.py:11-25](file://web/app.py#L11-L25)
- [main_web.py:63-70](file://main_web.py#L63-L70)
- [database/__init__.py:1-14](file://database/__init__.py#L1-L14)
- [database/db_manager.py:14-29](file://database/db_manager.py#L14-L29)
- [database/models.py:7-123](file://database/models.py#L7-L123)

**Section sources**
- [database/db_manager.py:14-29](file://database/db_manager.py#L14-L29)
- [database/models.py:7-123](file://database/models.py#L7-L123)
- [database/__init__.py:1-14](file://database/__init__.py#L1-L14)
- [web/app.py:11-25](file://web/app.py#L11-L25)
- [main_web.py:63-70](file://main_web.py#L63-L70)

## Core Components
- DatabaseManager: Central class that creates the SQLite engine, sets up sessions, and initializes tables. It provides methods to manage datasets, system configurations, generated data, executions, and training jobs.
- Declarative models: Define tables for datasets, generated data, system configurations, executions, and training jobs.
- Application integration: The web application constructs a global state containing a DatabaseManager instance and uses it across pages.

Key responsibilities:
- Engine and session creation
- Automatic schema initialization
- CRUD operations for all entities
- Status updates with timestamps

**Section sources**
- [database/db_manager.py:11-347](file://database/db_manager.py#L11-L347)
- [database/models.py:10-123](file://database/models.py#L10-L123)
- [web/app.py:11-25](file://web/app.py#L11-L25)

## Architecture Overview
The application uses a local SQLite database. On startup, the main entry point initializes the database manager, which creates the SQLite engine and ensures all tables exist. Pages in the web UI access the shared DatabaseManager instance to persist and retrieve data.

```mermaid
sequenceDiagram
participant User as "User"
participant Main as "main_web.py"
participant App as "web/app.py"
participant State as "AppState"
participant DBMgr as "DatabaseManager"
participant Engine as "SQLAlchemy Engine"
participant Models as "ORM Models"
User->>Main : Launch web UI
Main->>Main : check_and_install_dependencies()
Main->>Main : init_database()
Main->>DBMgr : DatabaseManager()
DBMgr->>Engine : create_engine("sqlite : ///...")
DBMgr->>Models : Base.metadata.create_all(engine)
Main-->>User : Ready
User->>App : Open UI
App->>State : AppState()
State->>DBMgr : DatabaseManager()
State-->>App : Shared DB instance
App-->>User : Render pages
```

**Diagram sources**
- [main_web.py:63-70](file://main_web.py#L63-L70)
- [database/db_manager.py:14-29](file://database/db_manager.py#L14-L29)
- [web/app.py:11-25](file://web/app.py#L11-L25)

## Detailed Component Analysis

### DatabaseManager Implementation
The DatabaseManager encapsulates:
- Engine creation with SQLite
- Session factory
- Automatic table creation via Base.metadata.create_all
- CRUD methods for datasets, system configurations, generated data, executions, and training jobs
- Timestamped status updates for executions and training jobs

```mermaid
classDiagram
class DatabaseManager {
+string db_path
+Engine engine
+SessionLocal
+__init__(db_path)
+get_session() Session
+create_dataset(...)
+get_dataset(id) Dataset
+get_all_datasets(type) Dataset[]
+delete_dataset(id) bool
+create_system_config(...)
+update_config_validation(id, is_valid, errors, execution_order)
+get_system_config(id) SystemConfig
+get_all_system_configs(only_valid) SystemConfig[]
+delete_system_config(id) bool
+create_generated_data(...)
+get_generated_data_by_config(id) GeneratedData[]
+get_generated_data_by_dataset(id) GeneratedData[]
+create_execution(...)
+update_execution_status(id, status, result, logs, error_message)
+get_execution(id) Execution
+get_all_executions(config_id) Execution[]
+create_training_job(...)
+update_training_status(id, status, logs, metrics, error_message, output_dir)
+get_training_job(id) TrainingJob
+get_all_training_jobs(type) TrainingJob[]
+delete_training_job(id) bool
}
class Dataset {
+int id
+string name
+string type
+string file_path
+string file_format
+int record_count
+datetime created_at
+datetime updated_at
}
class GeneratedData {
+int id
+int dataset_id
+int config_id
+string agent_id
+JSON input_data
+JSON output_data
+JSON trajectory
+JSON ground_truth
+JSON meta_info
+datetime created_at
}
class SystemConfig {
+int id
+string name
+boolean is_valid
+JSON config_json
+int agent_count
+JSON execution_order
+datetime created_at
+datetime updated_at
}
class Execution {
+int id
+int config_id
+int dataset_id
+string status
+JSON result
+Text logs
+Text error_message
+datetime started_at
+datetime completed_at
+datetime created_at
}
class TrainingJob {
+int id
+string name
+string type
+JSON config
+string status
+int dataset_id
+int config_id
+string output_dir
+string model_path
+JSON hyperparameters
+Text logs
+JSON metrics
+Text error_message
+datetime started_at
+datetime completed_at
+datetime created_at
+datetime updated_at
}
DatabaseManager --> Dataset : "manages"
DatabaseManager --> GeneratedData : "manages"
DatabaseManager --> SystemConfig : "manages"
DatabaseManager --> Execution : "manages"
DatabaseManager --> TrainingJob : "manages"
```

**Diagram sources**
- [database/db_manager.py:11-347](file://database/db_manager.py#L11-L347)
- [database/models.py:10-123](file://database/models.py#L10-L123)

**Section sources**
- [database/db_manager.py:11-347](file://database/db_manager.py#L11-L347)
- [database/models.py:10-123](file://database/models.py#L10-L123)

### Schema and Table Initialization
- The engine is created with a SQLite URL pointing to a local file path.
- The Base metadata is used to create all tables defined in models.
- The database path defaults to a local data directory under the project root.

```mermaid
flowchart TD
Start(["Startup"]) --> InitDB["Initialize DatabaseManager"]
InitDB --> BuildEngine["Create SQLite Engine"]
BuildEngine --> CreateTables["Create All Tables"]
CreateTables --> Ready(["Ready"])
```

**Diagram sources**
- [database/db_manager.py:14-29](file://database/db_manager.py#L14-L29)

**Section sources**
- [database/db_manager.py:14-29](file://database/db_manager.py#L14-L29)

### Connection Management and Lifecycle
- Sessions are created per operation using a local session maker bound to the engine.
- Each method opens a session, performs the operation, commits, and closes the session.
- The engine persists for the lifetime of the DatabaseManager instance.

```mermaid
sequenceDiagram
participant Caller as "Caller"
participant DB as "DatabaseManager"
participant Session as "Session"
participant Engine as "Engine"
Caller->>DB : get_session()
DB->>Session : SessionLocal()
Session-->>DB : Session instance
Caller->>DB : CRUD operation
DB->>Engine : Execute SQL
Engine-->>DB : Result
DB->>Session : commit/close
DB-->>Caller : Result
```

**Diagram sources**
- [database/db_manager.py:31-33](file://database/db_manager.py#L31-L33)
- [database/db_manager.py:41-56](file://database/db_manager.py#L41-L56)

**Section sources**
- [database/db_manager.py:31-33](file://database/db_manager.py#L31-L33)
- [database/db_manager.py:41-56](file://database/db_manager.py#L41-L56)

### Environment-Specific Settings and Setup
- Default database path: A local SQLite file located under a data directory in the project root.
- No explicit environment variable overrides are present in the codebase for the database path.
- The web UI entry point initializes the database during startup.

Setup steps:
- Install dependencies as defined in requirements.
- Launch the web UI; the database is initialized automatically.
- The application does not require a separate database service or credentials.

Environment guidance:
- Development: Use the default SQLite path for simplicity.
- Staging/Production: The current implementation uses a local file. To migrate to a remote database, adjust the engine URL and connection parameters accordingly.

**Section sources**
- [database/db_manager.py:14-21](file://database/db_manager.py#L14-L21)
- [main_web.py:63-70](file://main_web.py#L63-L70)
- [requirements.txt:1-19](file://requirements.txt#L1-L19)

### Backup and Restore Procedures
Current state:
- The application stores all data in a single SQLite file.
- There are no built-in backup or restore commands in the codebase.

Recommended procedure:
- Stop the application.
- Copy the SQLite database file to a safe location for backup.
- To restore, replace the database file with the backup copy and restart the application.

Note: This is a manual process and not automated by the application.

**Section sources**
- [database/db_manager.py:14-21](file://database/db_manager.py#L14-L21)

### Maintenance Tasks
- The application does not include dedicated maintenance scripts.
- Periodic cleanup of old execution and training job records can be performed by adding queries to remove stale entries.

**Section sources**
- [database/db_manager.py:205-263](file://database/db_manager.py#L205-L263)
- [database/db_manager.py:267-333](file://database/db_manager.py#L267-L333)

### Monitoring Strategies
- The application surfaces counts and statuses on the dashboard page.
- Training and execution pages display progress and logs.
- For deeper monitoring, integrate external tools to track file sizes, disk usage, and application logs.

**Section sources**
- [web/pages/dashboard.py:12-25](file://web/pages/dashboard.py#L12-L25)
- [web/pages/training.py:254-338](file://web/pages/training.py#L254-L338)
- [web/pages/execution_flow.py:116-223](file://web/pages/execution_flow.py#L116-L223)

### Security Considerations
- Connection encryption: The current SQLite engine URL does not specify SSL/TLS parameters. Encryption depends on filesystem-level protections.
- Credential management: No credentials are required for SQLite. Ensure file permissions restrict access to the database file.
- API keys: The configuration file contains API keys for external providers. Treat this file as sensitive and avoid committing it to version control.

**Section sources**
- [database/db_manager.py:21](file://database/db_manager.py#L21)
- [configs/api_config.yaml:1-9](file://configs/api_config.yaml#L1-L9)

## Dependency Analysis
The database layer depends on SQLAlchemy for ORM and engine management. The web application depends on the database module for persistence.

```mermaid
graph TB
REQ["requirements.txt<br/>sqlalchemy>=2.0.0"]
DBMOD["database/__init__.py"]
DBMGR["database/db_manager.py"]
MODELS["database/models.py"]
REQ --> DBMGR
DBMOD --> DBMGR
DBMGR --> MODELS
```

**Diagram sources**
- [requirements.txt:13-14](file://requirements.txt#L13-L14)
- [database/__init__.py:1-14](file://database/__init__.py#L1-L14)
- [database/db_manager.py:6-8](file://database/db_manager.py#L6-L8)

**Section sources**
- [requirements.txt:13-14](file://requirements.txt#L13-L14)
- [database/__init__.py:1-14](file://database/__init__.py#L1-L14)
- [database/db_manager.py:6-8](file://database/db_manager.py#L6-L8)

## Performance Considerations
- SQLite is lightweight and suitable for development and small-scale workloads.
- For higher concurrency or larger datasets, consider migrating to a client-server database with connection pooling and optimized indexing.
- The application currently uses a single engine/session factory; no explicit pool configuration is present.

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
Common issues and resolutions:
- Database not found or permission denied:
  - Verify the database file path exists and is writable.
  - Check file permissions on the database file and parent directory.
- Startup fails due to missing tables:
  - Ensure the application initializes the database manager during startup.
  - Confirm that table creation runs successfully.
- Session errors:
  - Ensure each operation properly commits and closes the session.
  - Avoid long-lived sessions to prevent memory growth.

**Section sources**
- [database/db_manager.py:14-29](file://database/db_manager.py#L14-L29)
- [database/db_manager.py:41-56](file://database/db_manager.py#L41-L56)

## Conclusion
The application uses a straightforward SQLite-based persistence layer with automatic schema initialization and a centralized DatabaseManager for all database operations. The web UI integrates the database seamlessly across pages. For production deployments, consider migrating to a more robust database engine, enabling encryption, and establishing automated backup and monitoring procedures.

[No sources needed since this section summarizes without analyzing specific files]

## Appendices

### Setup Instructions by Environment
- Development
  - Install dependencies from requirements.
  - Run the web UI; the database initializes automatically.
- Staging
  - Same as development; ensure the data directory is writable.
- Production
  - Same as development; ensure file permissions and backups are in place.
  - Consider migrating to a client-server database for scalability and reliability.

**Section sources**
- [requirements.txt:1-19](file://requirements.txt#L1-L19)
- [main_web.py:63-70](file://main_web.py#L63-L70)

### API Surface for Database Operations
- Datasets: create, read, list, delete
- SystemConfig: create, update validation, read, list, delete
- GeneratedData: create, filter by config/dataset
- Execution: create, update status with timestamps, read, list
- TrainingJob: create, update status with timestamps, read, list, delete

**Section sources**
- [database/db_manager.py:37-56](file://database/db_manager.py#L37-L56)
- [database/db_manager.py:110-155](file://database/db_manager.py#L110-L155)
- [database/db_manager.py:159-201](file://database/db_manager.py#L159-L201)
- [database/db_manager.py:205-263](file://database/db_manager.py#L205-L263)
- [database/db_manager.py:267-346](file://database/db_manager.py#L267-L346)