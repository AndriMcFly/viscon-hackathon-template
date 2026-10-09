from datetime import datetime, timedelta
from urllib.parse import unquote

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request, status

import ai
from models import TodoItem, TodoItemForCreate, User

# Load the .env file from the project root (Docker passes the variables in directly)
load_dotenv()

# Requests without login headers (public access, local development) share this user
GUEST_USER = User(id="guest", name="Guest")


def default_todos() -> list[TodoItem]:
    now = datetime.now()
    return [
        TodoItem(
            id=1,
            title="Find a great team",
            description="Find a great team to work with",
            deadline=now,
        ),
        TodoItem(
            id=2,
            title="Choose a project",
            description="Choose a project to work on",
            deadline=now + timedelta(hours=1),
        ),
        TodoItem(
            id=3,
            title="Interview people for need-finding",
            description="Interview people for need-finding",
            deadline=now + timedelta(hours=2),
        ),
        TodoItem(
            id=4,
            title="Come up with a lo-fi prototype",
            description="Come up with a lo-fi prototype",
            deadline=now + timedelta(hours=3),
        ),
    ]


class State:
    def __init__(self):
        # Mapping from user id to their todo items (in memory, lost on restart)
        self.todos_by_user_id: dict[str, list[TodoItem]] = {}

    def get_todos(self, user_id: str) -> list[TodoItem]:
        # When a new user id is seen, initialize with the default todos
        return self.todos_by_user_id.setdefault(user_id, default_todos())

    def create_todo(self, user_id: str, item: TodoItemForCreate) -> TodoItem:
        todos = self.get_todos(user_id)
        next_id = max((todo.id for todo in todos), default=0) + 1
        new_todo = TodoItem(
            id=next_id,
            title=item.title,
            description=item.description,
            deadline=item.deadline,
        )
        todos.append(new_todo)
        return new_todo

    def delete_todo(self, user_id: str, todo_id: int):
        todos = self.get_todos(user_id)
        self.todos_by_user_id[user_id] = [todo for todo in todos if todo.id != todo_id]


state = State()


app = FastAPI(docs_url="/api/docs", openapi_url="/api/openapi.json")


# Every endpoint that needs the current user calls this with its request
def extract_user(request: Request) -> User:
    id = request.headers.get("X-User-Id", "").strip()
    if not id:
        return GUEST_USER

    name = request.headers.get("X-User-Name")
    # The VIScon proxy percent-encodes non-ASCII characters (e.g. "Zo%C3%AB" -> "Zoë")
    name = unquote(name) if name else id

    return User(id=id, name=name)


@app.get("/api/me", response_model=User)
def auth_me(request: Request):
    return extract_user(request)


@app.get("/api/todos", response_model=list[TodoItem])
def get_todos(request: Request):
    user = extract_user(request)
    return state.get_todos(user.id)


@app.post("/api/todos", response_model=TodoItem, status_code=status.HTTP_201_CREATED)
def create_todo(request: Request, item: TodoItemForCreate):
    user = extract_user(request)
    return state.create_todo(user.id, item)


@app.delete("/api/todos/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(request: Request, todo_id: int):
    user = extract_user(request)
    state.delete_todo(user.id, todo_id)


@app.get("/api/todos/generate", response_model=TodoItemForCreate)
def generate_todo(prompt: str):
    try:
        todo = ai.generate_todo(prompt)
        if todo is not None:
            return todo
    except Exception as e:
        print(f"AI todo generation failed: {e!r}")

    # Fail gracefully: return a prefilled todo the user can complete by hand
    return TodoItemForCreate(title=prompt, description="", deadline=datetime.now())


if __name__ == "__main__":
    print("Starting server")
    uvicorn.run(
        "__main__:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
