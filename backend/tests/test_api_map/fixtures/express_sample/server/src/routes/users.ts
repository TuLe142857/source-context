import { Router } from "express";

export const usersRouter = Router();

usersRouter.get("/:id", async (req, res) => {
  res.json({ id: req.params.id });
});

usersRouter.post("/", createUser);

usersRouter.delete("/:id", (req, res) => res.sendStatus(204));

function createUser(req: unknown, res: { sendStatus(code: number): void }) {
  res.sendStatus(201);
}
