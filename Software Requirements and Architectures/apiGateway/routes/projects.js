var express = require("express");
var router = express.Router();

const axios = require("axios");

const https = require("https");
const fs = require("fs");

const multer = require("multer");
const FormData = require("form-data");

const auth = require("../auth/auth");

const key = fs.readFileSync(__dirname + "/../certs/selfsigned.key");
const cert = fs.readFileSync(__dirname + "/../certs/selfsigned.crt");

const httpsAgent = new https.Agent({
  rejectUnauthorized: false, // (NOTE: this will disable client verification)
  cert: cert,
  key: key,
});

const storage = multer.memoryStorage();
const upload = multer({ storage: storage });

const projectsURL = "https://projects:9001/";

// TODO Verify jwt

/*
Project structure
{
    "_id": Mongoose.type.id,
    "user_id": Mongoose.type.id,
    "name": String,
    "imgs": [Image Structure],
    "tools": [Tool Structure],
}

Image structure
{
    "_id": Mongoose.type.id,
    "og_uri": String,
    "new_uri": String
}

Tool structure
{
    "_id": Mongoose.type._id,
    "position": Number,
    "procedure": String,
    "params": Object
}

Post answer structure in case of success
{
    "acknowledged": Bool,
    "modifiedCount": Number,
    "upsertedId": null,
    "upsertedCount": Number,
    "matchedCount": Number
}
*/

/**
 * Note: auth.checkToken is a midleware used to verify JWT
 */

/**
 * Share endpoints proxy
 * These forward requests to the projects service's /share routes.
 */
router.post("/share", auth.checkToken, function (req, res, next) {
  const headers = {};
  if (req.headers && req.headers.authorization) {
    headers.authorization = req.headers.authorization;
  }

  axios
    .post(projectsURL + `share`, req.body, {
      headers,
      httpsAgent: httpsAgent,
    })
    .then((resp) => res.status(resp.status).jsonp(resp.data))
    .catch((err) => {
      console.error("Error creating share link:", err.response?.status, err.response?.data);
      const status = err.response?.status || 500;
      res.status(status).jsonp("Error creating share link");
    });
});

router.delete("/share/:token", auth.checkToken, function (req, res, next) {
  const headers = {};
  if (req.headers && req.headers.authorization) {
    headers.authorization = req.headers.authorization;
  }

  axios
    .delete(projectsURL + `share/${req.params.token}`, {
      headers,
      httpsAgent: httpsAgent,
    })
    .then((resp) => res.status(resp.status).jsonp(resp.data))
    .catch((err) => {
      console.error("Error revoking share link:", err.response?.status, err.response?.data);
      const status = err.response?.status || 500;
      res.status(status).jsonp("Error revoking share link");
    });
});

router.get("/share/:token", function (req, res, next) {
  const headers = {};
  if (req.headers && req.headers.authorization) headers.authorization = req.headers.authorization;

  axios
    .get(projectsURL + `share/${req.params.token}`, {
      headers,
      httpsAgent: httpsAgent,
    })
    .then((resp) => res.status(resp.status).jsonp(resp.data))
    .catch((err) => {
      console.error("Error accessing shared project:", err.response?.status, err.response?.data);
      const status = err.response?.status || 500;
      res.status(status).jsonp("Error accessing shared project");
    });
});

/**
 * Get user's projects
 * @body Empty
 * @returns List of projects, each project has no information about it's images or tools
 */
router.get("/:user", auth.checkToken, function (req, res, next) {
  axios
    .get(projectsURL + `${req.params.user}`, { httpsAgent: httpsAgent })
    .then((resp) => res.status(200).jsonp(resp.data))
    .catch((err) => res.status(500).jsonp("Error getting users"));
});

/**
 * Get user's project
 * @body Empty
 * @returns The required project
 */
router.get("/:user/:project", auth.checkToken, function (req, res, next) {
  axios
    .get(projectsURL + `${req.params.user}/${req.params.project}`, {
      httpsAgent: httpsAgent,
    })
    .then((resp) => res.status(200).jsonp(resp.data))
    .catch((err) => res.status(500).jsonp("Error getting project"));
});

/**
 * Get project image
 * @body Empty
 * @returns The image url
 */
router.get(
  "/:user/:project/img/:img",
  auth.checkToken,
  function (req, res, next) {
    axios
      .get(
        projectsURL +
          `${req.params.user}/${req.params.project}/img/${req.params.img}`,
        {
          httpsAgent: httpsAgent,
        }
      )
      .then((resp) => {
        res.status(200).send(resp.data);
      })
      .catch((err) => res.status(500).jsonp("Error getting project image"));
  }
);

/**
 * Get project images
 * @body Empty
 * @returns The project's images
 */
router.get("/:user/:project/imgs", auth.checkToken, function (req, res, next) {
  axios
    .get(projectsURL + `${req.params.user}/${req.params.project}/imgs`, {
      httpsAgent: httpsAgent,
    })
    .then((resp) => {
      res.status(200).send(resp.data);
    })
    .catch((err) => res.status(500).jsonp("Error getting project images"));
});

/**
 * Get project's processment result
 * @body Empty
 * @returns The required results, sent as a zip
 */
router.get(
  "/:user/:project/process",
  auth.checkToken,
  function (req, res, next) {
    axios
      .get(projectsURL + `${req.params.user}/${req.params.project}/process`, {
        httpsAgent: httpsAgent,
        responseType: "arraybuffer",
      })
      .then((resp) => res.status(200).send(resp.data))
      .catch((err) =>
        res.status(500).jsonp("Error getting processing results file")
      );
  }
);

/**
 * Get project's processment result
 * @body Empty
 * @returns The required results, sent as [{img_id, img_name, url}]
 */
router.get(
  "/:user/:project/process/url",
  auth.checkToken,
  function (req, res, next) {
    axios
      .get(
        projectsURL + `${req.params.user}/${req.params.project}/process/url`,
        {
          httpsAgent: httpsAgent,
        }
      )
      .then((resp) => {
        res.status(200).send(resp.data);
      })
      .catch((err) =>
        res.status(500).jsonp("Error getting processing results")
      );
  }
);

/**
 * Create new user's project
 * @body { "name": String }
 * @returns Created project's data
 */
router.post("/:user", auth.checkToken, function (req, res, next) {
  axios
    .post(projectsURL + `${req.params.user}`, req.body, {
      httpsAgent: httpsAgent,
    })
    .then((resp) => res.status(201).jsonp(resp.data))
    .catch((err) => res.status(500).jsonp("Error creating new project"));
});

/**
 * Preview an image
 * @body Empty
 * @returns String indication preview is being processed
 */
router.post(
  "/:user/:project/preview/:img",
  auth.checkToken,
  function (req, res, next) {
    axios
      .post(
        projectsURL +
          `${req.params.user}/${req.params.project}/preview/${req.params.img}`,
        req.body,
        { httpsAgent: httpsAgent }
      )
      .then((resp) => res.status(201).jsonp(resp.data))
      .catch((err) => {
        console.log(err);
        res.status(500).jsonp("Error requesting image preview");
      });
  }
);

/**
 * Add image to project
 * @body Empty
 * @file Image to be added
 * @returns Post answer structure in case of success
 */
router.post(
  "/:user/:project/img",
  upload.single("image"),
  auth.checkToken,
  function (req, res, next) {
    const data = new FormData();
    data.append("image", req.file.buffer, {
      filename: req.file.originalname,
      contentType: req.file.mimetype,
    });

    axios
      .post(
        projectsURL + `${req.params.user}/${req.params.project}/img`,
        data,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
          httpsAgent: httpsAgent,
        }
      )
      .then((resp) => res.sendStatus(201))
      .catch((err) => res.status(500).jsonp("Error adding image to project"));
  }
);

/**
 * Add tool to project
 * @body { "procedure": String, "params": Object }
 * @returns Post answer structure in case of success
 */
router.post("/:user/:project/tool", auth.checkToken, function (req, res, next) {
  axios
    .post(
      projectsURL + `${req.params.user}/${req.params.project}/tool`,
      req.body,
      { httpsAgent: httpsAgent }
    )
    .then((resp) => res.status(201).jsonp(resp.data))
    .catch((err) => res.status(500).jsonp("Error adding tool to project"));
});

/**
 * Reorder tools of a project
 * @body [{ "position": Number, "procedure": String, "params": Object }] (Position is a unique number between 0 and req.body.length - 1)
 * @returns Post answer structure in case of success
 */
router.post(
  "/:user/:project/reorder",
  auth.checkToken,
  function (req, res, next) {
    axios
      .post(
        projectsURL + `${req.params.user}/${req.params.project}/reorder`,
        req.body,
        { httpsAgent: httpsAgent }
      )
      .then((resp) => res.status(201).jsonp(resp.data))
      .catch((err) => res.status(500).jsonp("Error reordering tools"));
  }
);

/**
 * Generate request to process a project
 * @body Empty
 * @returns String indicating process request has been created
 */
router.post(
  "/:user/:project/process",
  auth.checkToken,
  function (req, res, next) {
    axios
      .post(
        projectsURL + `${req.params.user}/${req.params.project}/process`,
        req.body,
        { httpsAgent: httpsAgent }
      )
      .then((resp) => res.status(201).jsonp(resp.data))
      .catch((err) => {
        const status = err.response?.status || 500;
        const message = err.response?.data || "Error requesting project processing";
        res.status(status).jsonp(message);
      });
  }
);

/**
 * Update a specific project
 * @body { "name": String }
 * @returns Empty
 */
router.put("/:user/:project", auth.checkToken, function (req, res, next) {
  axios
    .put(projectsURL + `${req.params.user}/${req.params.project}`, req.body, {
      httpsAgent: httpsAgent,
    })
    .then((_) => res.sendStatus(204))
    .catch((err) => res.status(500).jsonp("Error updating project details"));
});

/**
 * Update a tool from a project
 * @body { "params" : Object }
 * @returns Empty
 */
router.put(
  "/:user/:project/tool/:tool",
  auth.checkToken,
  function (req, res, next) {
    axios
      .put(
        projectsURL +
          `${req.params.user}/${req.params.project}/tool/${req.params.tool}`,
        req.body,
        { httpsAgent: httpsAgent }
      )
      .then((_) => res.sendStatus(204))
      .catch((err) => res.status(500).jsonp("Error updating tool params"));
  }
);

/**
 * Delete a user's project
 * @body Empty
 * @returns Empty
 */
router.delete("/:user/:project", auth.checkToken, function (req, res, next) {
  axios
    .delete(projectsURL + `${req.params.user}/${req.params.project}`, {
      httpsAgent: httpsAgent,
    })
    .then((_) => res.sendStatus(204))
    .catch((err) => res.status(500).jsonp("Error deleting project"));
});

/**
 * Remove an image from a user's project
 * @body Empty
 * @returns Empty
 */
router.delete(
  "/:user/:project/img/:img",
  auth.checkToken,
  function (req, res, next) {
    axios
      .delete(
        projectsURL +
          `${req.params.user}/${req.params.project}/img/${req.params.img}`,
        { httpsAgent: httpsAgent }
      )
      .then((_) => res.sendStatus(204))
      .catch((err) =>
        res.status(500).jsonp("Error deleting image from project")
      );
  }
);

/**
 * Remove a tool from a user's project
 * @body Empty
 * @returns Empty
 */
router.delete(
  "/:user/:project/tool/:tool",
  auth.checkToken,
  function (req, res, next) {
    axios
      .delete(
        projectsURL +
          `${req.params.user}/${req.params.project}/tool/${req.params.tool}`,
        { httpsAgent: httpsAgent }
      )
      .then((_) => res.sendStatus(204))
      .catch((err) =>
        res.status(500).jsonp("Error removing tool from project")
      );
  }
);

/**
 * Cancel processing of a project
 * @body Empty
 * @returns Message indicating processing has been cancelled
 */
router.post(
  "/:user/:project/cancel",
  auth.checkToken,
  function (req, res, next) {
    axios
      .post(
        projectsURL + `${req.params.user}/${req.params.project}/cancel`,
        req.body,
        { httpsAgent: httpsAgent }
      )
      .then((resp) => res.status(200).jsonp(resp.data))
      .catch((err) =>
        res.status(500).jsonp("Error cancelling project processing")
      );
  }
);

module.exports = router;

/**
 * Share endpoints proxy
 * These forward requests to the projects service's /share routes.
 */
router.post("/share", auth.checkToken, function (req, res, next) {
  console.log("API Gateway /share route handler - proxying to projects service");
  const headers = {};
  if (req.headers && req.headers.authorization) {
    headers.authorization = req.headers.authorization;
    console.log("Forwarding authorization header to projects service:", headers.authorization.substring(0, 50) + "...");
  }

  axios
    .post(projectsURL + `share`, req.body, {
      headers,
      httpsAgent: httpsAgent,
    })
    .then((resp) => {
      console.log("Projects service responded with status:", resp.status);
      res.status(resp.status).jsonp(resp.data);
    })
    .catch((err) => {
      console.error("Error proxying POST /share", err.message || err);
      console.error("Projects service response status:", err.response?.status);
      console.error("Projects service response data:", err.response?.data);
      const status = err.response?.status || 500;
      res.status(status).jsonp("Error creating share link");
    });
});

router.delete("/share/:token", auth.checkToken, function (req, res, next) {
  console.log("API Gateway /share/:token DELETE route handler - proxying to projects service");
  const headers = {};
  if (req.headers && req.headers.authorization) {
    headers.authorization = req.headers.authorization;
    console.log("Forwarding authorization header to projects service");
  }

  axios
    .delete(projectsURL + `share/${req.params.token}`, {
      headers,
      httpsAgent: httpsAgent,
    })
    .then((resp) => {
      console.log("Projects service responded with status:", resp.status);
      res.status(resp.status).jsonp(resp.data);
    })
    .catch((err) => {
      console.error("Error proxying DELETE /share/:token", err.message || err);
      console.error("Projects service response status:", err.response?.status);
      const status = err.response?.status || 500;
      res.status(status).jsonp("Error revoking share link");
    });
});

router.get("/share/:token", function (req, res, next) {
  const headers = {};
  if (req.headers && req.headers.authorization) headers.Authorization = req.headers.authorization;

  axios
    .get(projectsURL + `share/${req.params.token}`, {
      headers,
      httpsAgent: httpsAgent,
    })
    .then((resp) => res.status(resp.status).jsonp(resp.data))
    .catch((err) => {
      console.error("Error proxying GET /share/:token", err.message || err);
      const status = err.response?.status || 500;
      res.status(status).jsonp("Error accessing shared project");
    });
});

router.post("/share/:token/copy", auth.checkToken, function (req, res, next) {
  console.log("API Gateway /share/:token/copy route handler - proxying to projects service");
  const headers = {};
  if (req.headers && req.headers.authorization) {
    headers.authorization = req.headers.authorization;
  }

  axios
    .post(projectsURL + `share/${req.params.token}/copy`, req.body, {
      headers,
      httpsAgent: httpsAgent,
    })
    .then((resp) => {
      console.log("Projects service responded with status:", resp.status);
      res.status(resp.status).jsonp(resp.data);
    })
    .catch((err) => {
      console.error("Error proxying POST /share/:token/copy", err.message || err);
      const status = err.response?.status || 500;
      res.status(status).jsonp(err.response?.data || "Error copying project");
    });
});

router.get("/share/:token/image/:imageId", function (req, res, next) {
  console.log("API Gateway /share/:token/image/:imageId - proxying to projects service");

  axios
    .get(projectsURL + `share/${req.params.token}/image/${req.params.imageId}`, {
      httpsAgent: httpsAgent,
    })
    .then((resp) => {
      res.status(resp.status).jsonp(resp.data);
    })
    .catch((err) => {
      console.error("Error proxying GET /share/:token/image/:imageId", err.message || err);
      const status = err.response?.status || 500;
      res.status(status).jsonp(err.response?.data || "Error getting shared image");
    });
});

router.post("/share/:token/access", auth.checkToken, function (req, res, next) {
  console.log("API Gateway /share/:token/access - proxying to projects service");
  const headers = {};
  if (req.headers && req.headers.authorization) {
    headers.authorization = req.headers.authorization;
  }

  axios
    .post(projectsURL + `share/${req.params.token}/access`, req.body, {
      headers,
      httpsAgent: httpsAgent,
    })
    .then((resp) => {
      res.status(resp.status).jsonp(resp.data);
    })
    .catch((err) => {
      console.error("Error proxying POST /share/:token/access", err.message || err);
      const status = err.response?.status || 500;
      res.status(status).jsonp(err.response?.data || "Error accessing shared project");
    });
}); 