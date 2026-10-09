import { useEffect, useState } from "react";
import { getTodos, type TodoItem, type User } from "../api";
import TodoForm from "./TodoForm";
import TodoTable from "./TodoTable";
import "./Todos.css";

interface TodosProps {
  me?: User;
}

const Todos = ({ me }: TodosProps) => {
  const [todos, setTodos] = useState<TodoItem[]>([]);

  function updateTodos() {
    getTodos().then(setTodos);
  }

  useEffect(() => {
    updateTodos();
  }, []);

  return (
    <main className="todos">
      <h2>{me ? `Todos of ${me.name}` : "Your todos"}</h2>
      <TodoForm onTodoCreated={updateTodos} />
      <TodoTable todos={todos} onTodoDeleted={updateTodos} />
    </main>
  );
};

export default Todos;
