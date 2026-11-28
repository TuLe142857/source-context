import express from "express";
import { usersRouter } from "./routes/users";
import ordersRouter from "./routes/orders";

const app = express();
const API_PREFIX = "/api/v1";

app.use(express.json());
app.use(`${API_PREFIX}/users`, usersRouter);
app.use("/api/v1/orders", ordersRouter);

app.get("/health", (req, res) => res.json({ ok: true }));

function listProducts(req: express.Request, res: express.Response) {
  res.json([]);
}

app.route("/api/v1/products").get(listProducts).post((req, res) => res.sendStatus(201));

export default app;
