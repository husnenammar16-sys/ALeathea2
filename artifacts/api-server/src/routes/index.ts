import { Router, type IRouter } from "express";
import healthRouter from "./health";
import alythiaRouter from "./alythia";

const router: IRouter = Router();

router.use(healthRouter);
router.use(alythiaRouter);

export default router;
