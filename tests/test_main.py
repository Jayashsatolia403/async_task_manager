import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
from app.models import TaskStatus

@pytest.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()

pytestmark = pytest.mark.asyncio

async def test_create_task(client: AsyncClient, db_session: AsyncSession):
    response = await client.post("/tasks", json={"title": "Test Task 1", "description": "Test Description", "priority": 3})
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Task 1"
    assert data["status"] == "pending"
    assert "id" in data

    log_response = await client.get(f"/tasks/{data['id']}/logs")
    assert log_response.status_code == 200
    logs = log_response.json()
    assert len(logs) > 0
    assert logs[0]["status"] == "Task created with status pending"


async def test_list_tasks(client: AsyncClient, db_session: AsyncSession):
    await client.post("/tasks", json={"title": "Task A - List", "description": "Desc A", "priority": 1})
    await client.post("/tasks", json={"title": "Task B - List", "description": "Desc B", "priority": 5, "status": "in_progress"})

    response = await client.get("/tasks?page=1&size=5")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2
    assert len(data["items"]) >= 2
    assert data["items"][0]["priority"] == 5

    response_filtered = await client.get("/tasks?status=in_progress")
    assert response_filtered.status_code == 200
    data_filtered = response_filtered.json()
    assert len(data_filtered["items"]) >= 1
    assert data_filtered["items"][0]["title"] == "Task B - List"


async def test_get_task(client: AsyncClient, db_session: AsyncSession):
    create_response = await client.post("/tasks", json={"title": "Fetch Me", "priority": 2})
    task_id = create_response.json()["id"]

    response = await client.get(f"/tasks/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Fetch Me"

    response_not_found = await client.get("/tasks/99999")
    assert response_not_found.status_code == 404


async def test_update_task(client: AsyncClient, db_session: AsyncSession):
    create_response = await client.post("/tasks", json={"title": "Update Me", "priority": 1})
    task_id = create_response.json()["id"]

    update_payload = {"title": "Updated Title", "status": "completed", "priority": 5}
    response = await client.put(f"/tasks/{task_id}", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["status"] == "completed"
    assert data["priority"] == 5

    log_response = await client.get(f"/tasks/{task_id}/logs?size=5")
    logs = log_response.json()
    status_change_logged = any("Status changed from pending to completed" in log["status"] for log in logs)
    assert status_change_logged


async def test_delete_task(client: AsyncClient, db_session: AsyncSession):
    create_response = await client.post("/tasks", json={"title": "Delete Me", "priority": 1})
    task_id = create_response.json()["id"]

    response = await client.delete(f"/tasks/{task_id}")
    assert response.status_code == 204

    get_response = await client.get(f"/tasks/{task_id}")
    assert get_response.status_code == 404


async def test_process_task_background(client: AsyncClient, db_session: AsyncSession, mocker):
    create_response = await client.post("/tasks", json={"title": "Process Me", "priority": 4})
    task_id = create_response.json()["id"]

    mocked_process = mocker.patch("app.main.process_task_in_background")

    response = await client.post(f"/tasks/{task_id}/process")
    assert response.status_code == 202
    assert response.json()["message"] == "Task processing started in the background."

    await asyncio.sleep(0.1)

    log_response = await client.get(f"/tasks/{task_id}/logs")
    logs = log_response.json()
    initiated_log_present = any("Task processing initiated in background" in log["status"] for log in logs)
    assert initiated_log_present

    mocked_process.assert_called_once_with(task_id)


async def test_process_task_already_in_progress(client: AsyncClient):
    create_resp = await client.post("/tasks", json={"title": "Busy Task", "priority": 1})
    task_id = create_resp.json()["id"]
    await client.put(f"/tasks/{task_id}", json={"status": TaskStatus.IN_PROGRESS.value})

    response = await client.post(f"/tasks/{task_id}/process")
    assert response.status_code == 400
    assert "Task is already in_progress" in response.json()["detail"]


async def test_process_task_completed(client: AsyncClient):
    create_resp = await client.post("/tasks", json={"title": "Done Task", "priority": 1})
    task_id = create_resp.json()["id"]
    await client.put(f"/tasks/{task_id}", json={"status": TaskStatus.COMPLETED.value})

    response = await client.post(f"/tasks/{task_id}/process")
    assert response.status_code == 400
    assert "Task is already completed" in response.json()["detail"]
