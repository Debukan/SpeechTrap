import React, { useEffect, useState } from "react";
import { fetchUsers } from "../api/apiClient";

const UserList = () => {
  const [users, setUsers] = useState([]);

  useEffect(() => {
    const getUsers = async () => {
      try {
        const userList = await fetchUsers();
        setUsers(userList);
      } catch (error) {
        console.error("Failed to fetch users");
      }
    };

    getUsers();
  }, []);

  return (
    <div>
      <h2>User List</h2>
      <ul>
        {users.map((user) => (
          <li key={user.id}>{user.username}</li>
        ))}
      </ul>
    </div>
  );
};

export default UserList;