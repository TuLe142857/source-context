import axios from "axios";

const BASE_URL = process.env.USERS_URL || "http://users:3000";
const http = axios.create({ baseURL: `${BASE_URL}/api/v1` });

export async function getUser(id) {
  const { data } = await http.get(`/users/${id}`);
  return data;
}

export function createOrder(order) {
  return axios.post("http://users:3000/api/v1/orders", order);
}

export async function updateStatus(orderId, status) {
  return fetch(`${BASE_URL}/api/v1/orders/${orderId}/status`, {
    method: "PUT",
    body: JSON.stringify({ status }),
  });
}

export function removeUser(id) {
  return axios({ method: "delete", url: `${BASE_URL}/api/v1/users/${id}` });
}

export function account(id) {
  return fetch(`/api/accounts/${id}`).then((response) => response.json());
}

const cache = new Map();

export function cached(key) {
  return cache.get(`/users/${key}`);
}
