const mongoose = require("mongoose");

const daySchema = new mongoose.Schema({
  day: { type: Date, required: true },
  processed: { type: Number, default: 0, required: true },
});

const userSchema = new mongoose.Schema({
  name: { type: String, required: false },
  email: { type: String, sparse: true, unique: true, required: false },
  password_hash: { type: String, required: false },
  type: {
    type: String,
    enum: ["anonymous", "free", "premium"],
    default: "free",
    required: true,
  },
  operations: { type: [daySchema], required: true, default: [] },
});

async function userCleanup() {
  const userId = this._id.toString();

  try {
    const projectCtrl = require("../../projects/controllers/project");
    const resultCtrl = require("../../projects/controllers/result");
    const { delete_image } = require("../../projects/utils/minio");
    const subscriptionCtrl = require("../../subscriptions/controllers/subscription");
    const axios = require("axios");

    // get all projects
    const projects = await projectCtrl.getAll(userId);
    for (const p of projects) {
      for (const img of (p.imgs || [])) { // if no projects, use empty list
        try {
          // delete source image
          await delete_image(userId, p._id.toString(), "src", img.og_img_key);
        } catch (e) {}
        try {
          // delete preview image
          await delete_image(userId, p._id.toString(), "preview", img.og_img_key);
        } catch (e) {}
        try {
          // delete output image
          await delete_image(userId, p._id.toString(), "out", img.og_img_key);
        } catch (e) {}
      }

      // get all results for project
      const results = await resultCtrl.getAll(userId, p._id);
      for (const r of results) {
        try {
          // delete result image
          await delete_image(userId, p._id.toString(), "out", r.img_key);
        } catch (e) {}
        try {
          // delete result document
          await resultCtrl.delete(userId, p._id, r.img_id);
        } catch (e) {}
      }

      try {
        // delete the project itself
        await projectCtrl.delete(userId, p._id);
      } catch (e) {}
    }

    // delete all subscriptions
    const subs = await subscriptionCtrl.getSubscriptionsByUserId(userId);
    for (const s of (subs || [])) {
      try {
        await subscriptionCtrl.deleteOne(s._id);
      } catch (e) {}
    }

    try {
      // delete the user's bucket
      await axios.delete(`http://img_storage:11000/delete/bucket/${userId}`);
    } catch (e) {
      console.warn(`Bucket deletion failed for user ${userId}:`, e.message);
    }
  } catch (err) {
    console.error("user pre-remove cleanup error:", err && err.message ? err.message : err);
  }
}

// run cleanup when document remove/deleteOne is called
userSchema.pre("remove", userCleanup);
userSchema.pre("deleteOne", { document: true, query: false }, userCleanup);

module.exports = mongoose.model("user", userSchema);
