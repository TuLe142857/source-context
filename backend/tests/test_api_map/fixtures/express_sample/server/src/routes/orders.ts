import * as express from "express";

const router = express.Router();

const updateStatus = (req: express.Request, res: express.Response) => {
  res.json({});
};

router.get("/:orderId", (req, res) => res.json({}));
router.put("/:orderId/status", updateStatus);

export default router;
