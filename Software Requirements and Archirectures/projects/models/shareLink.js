const mongoose = require("mongoose");

const shareLinkSchema = new mongoose.Schema({
  token: {
    type: String,
    required: true,
    unique: true,
    index: true
  },

  project_id: {
    type: mongoose.Schema.Types.ObjectId,
    ref: "project",
    required: true
  },

  owner_id: {
    type: mongoose.Schema.Types.ObjectId,
    required: true
  },

  permission: {
    type: String,
    enum: ["read", "edit", "collaborate"], 
    default: "read"
  },

  revoked: {
    type: Boolean,
    default: false
  },

  createdAt: {
    type: Date,
    default: Date.now
  }
});

module.exports = mongoose.model("shareLink", shareLinkSchema);