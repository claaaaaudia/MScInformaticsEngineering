const mongoose = require("mongoose");

const toolSchema = new mongoose.Schema({
  position: { type: Number, required: true },
  procedure: { type: String, required: true },
  params: { type: mongoose.Schema.Types.Mixed, required: true },
});

const imgSchema = new mongoose.Schema({
  og_uri: { type: String, required: true },
  new_uri: { type: String, required: true },
  og_img_key: { type: String, required: true },
});

const projectSchema = new mongoose.Schema({
  name: { type: String, required: true },
  user_id: { type: mongoose.Schema.Types.ObjectId, required: true }, // Original owner
  collaborators: { 
    type: [mongoose.Schema.Types.ObjectId], 
    default: [] 
  },
  imgs: { type: [imgSchema], default: [] },
  tools: { type: [toolSchema], default: [] },
});

module.exports = mongoose.model("project", projectSchema);