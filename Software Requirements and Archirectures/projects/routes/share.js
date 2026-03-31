const express = require("express");
const router = express.Router();
const controller = require("../controllers/share");
const auth = require("../auth/auth").checkToken;

// Criar link
router.post("/", auth, controller.createLink);

// Revogar link
router.delete("/:token", auth, controller.revokeLink);

// Aceder por link
router.get("/:token", controller.accessByLink);

// Get image from shared project (read-only, no auth required)
router.get("/:token/image/:imageId", controller.getSharedProjectImage);

// Join collaborative project OR copy project (requires authentication)
router.post("/:token/access", auth, controller.accessSharedProject);

module.exports = router;