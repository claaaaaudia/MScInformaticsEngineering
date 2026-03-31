const crypto = require("crypto");
const ShareLink = require("../models/shareLink");
const Project = require("../models/project");
const axios = require("axios");
const FormData = require("form-data");
const { get_image_docker, post_image } = require("../utils/minio");

// Criar link de partilha
module.exports.createLink = async (req, res) => {
  try {
    const { projectId, permission } = req.body;
    const userId = req.user.id;

    const project = await Project.findOne({
      _id: projectId,
      user_id: userId
    });

    if (!project)
      return res.status(403).json({ error: "Not project owner" });

    const token = crypto.randomBytes(32).toString("hex");

    const link = await ShareLink.create({
      token,
      project_id: projectId,
      owner_id: userId,
      permission: permission || "read"
    });

    res.json({
      shareUrl: `${process.env.FRONTEND_URL}/share/${token}`,
      token,
    });

  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};


//Revogar link
module.exports.revokeLink = async (req, res) => {
  try {
    const { token } = req.params;
    const userId = req.user.id;

    const link = await ShareLink.findOne({ token });

    if (!link || link.owner_id.toString() !== userId)
      return res.status(403).json({ error: "Unauthorized" });

    link.revoked = true;
    await link.save();

    res.json({ message: "Link revoked successfully" });

  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};


// Aceder a projeto por link
module.exports.accessByLink = async (req, res) => {
  try {
    const { token } = req.params;

    const link = await ShareLink.findOne({ token });

    if (!link || link.revoked)
      return res.status(403).json({ error: "Invalid or revoked link" });

    const project = await Project.findById(link.project_id);

    if (!project)
      return res.status(404).json({ error: "Project not found" });

    res.json({
      project,
      permission: link.permission
    });

  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};

// Copy project to user's account
module.exports.copyProjectByLink = async (req, res) => {
  try {
    const { token } = req.params;
    const userId = req.user.id;
    const link = await ShareLink.findOne({ token });

    if (!link || link.revoked)
      return res.status(403).json({ error: "Invalid or revoked link" });

    const originalProject = await Project.findById(link.project_id);

    if (!originalProject)
      return res.status(404).json({ error: "Project not found" });

    const existingCopy = await Project.findOne({
      user_id: userId,
      name: new RegExp(`^${originalProject.name}( \\(shared project( \\d+)?\\))?$`)
    });

    let projectName = `${originalProject.name} (shared project)`;
    
    if (existingCopy) {
      const allCopies = await Project.find({
        user_id: userId,
        name: new RegExp(`^${originalProject.name}( \\(shared project( \\d+)?\\))?$`)
      });
      
      const copyNumbers = allCopies
        .map(p => {
          const match = p.name.match(/\(shared project (\d+)\)/);
          return match ? parseInt(match[1]) : 1;
        });
      
      const nextNumber = copyNumbers.length > 0 ? Math.max(...copyNumbers) + 1 : 2;
      projectName = `${originalProject.name} (shared project ${nextNumber})`;
    }

    const newProject = await Project.create({
      name: projectName,
      user_id: userId,
      imgs: [],
      tools: originalProject.tools
        .filter(tool => tool.procedure && tool.params !== undefined)
        .map(tool => ({
          position: tool.position,
          procedure: tool.procedure,
          params: tool.params || {}
        }))
    });

    const copiedImages = [];
    
    for (const img of originalProject.imgs) {
      try {
        
        const imageResp = await get_image_docker(
          originalProject.user_id,
          originalProject._id,
          "src",
          img.og_img_key
        );
        
        const imageUrl = imageResp.data.url;
        
        const fileResp = await axios.get(imageUrl, { 
          responseType: 'arraybuffer'
        });
        
        const filename = img.og_uri.split('/').pop();
        
        const formData = new FormData();
        formData.append('file', Buffer.from(fileResp.data), {
          filename: filename,
          contentType: fileResp.headers['content-type'] || 'image/jpeg'
        });
        
        const uploadResp = await post_image(
          userId,
          newProject._id,
          "src",
          formData
        );
        
        const newImageKey = uploadResp.data.data.imageKey.split("/").pop();
        
        copiedImages.push({
          og_uri: `./images/users/${userId}/projects/${newProject._id}/src/${filename}`,
          new_uri: `./images/users/${userId}/projects/${newProject._id}/out/${filename}`,
          og_img_key: newImageKey
        });
        
      } catch (imgError) {
        console.error(`Error copying image ${img.og_img_key}:`, imgError);
      }
    }

    await Project.updateOne(
      { _id: newProject._id },
      { imgs: copiedImages }
    );

    res.status(201).json({
      projectId: newProject._id,
      message: "Project copied successfully",
      imagesCopied: copiedImages.length,
      totalImages: originalProject.imgs.length
    });

  } catch (err) {
    console.error("Error copying project:", err);
    res.status(500).json({ error: err.message });
  }
};

module.exports.getSharedProjectImage = async (req, res) => {
  try {
    const { token, imageId } = req.params;

    const link = await ShareLink.findOne({ token, revoked: false });

    if (!link)
      return res.status(403).json({ error: "Invalid or revoked link" });

    const project = await Project.findById(link.project_id);

    if (!project)
      return res.status(404).json({ error: "Project not found" });

    const image = project.imgs.find(img => img._id.toString() === imageId);

    if (!image)
      return res.status(404).json({ error: "Image not found" });

    const { get_image_host } = require("../utils/minio");
    const resp = await get_image_host(
      project.user_id,
      project._id,
      "src",
      image.og_img_key
    );

    res.json({
      _id: image._id,
      name: image.og_uri.split('/').pop(),
      url: resp.data.url
    });

  } catch (err) {
    console.error("Error getting shared image:", err);
    res.status(500).json({ error: err.message });
  }
};

module.exports.accessSharedProject = async (req, res) => {
  try {
    const { token } = req.params;
    const userId = req.user.id;

    console.log(`User ${userId} accessing shared project with token ${token}`);

    const link = await ShareLink.findOne({ token });

    if (!link || link.revoked)
      return res.status(403).json({ error: "Invalid or revoked link" });

    const project = await Project.findById(link.project_id);

    if (!project)
      return res.status(404).json({ error: "Project not found" });

    console.log(`Found project: ${project._id}, permission: ${link.permission}`);

    if (link.permission === "collaborate") {
      const isOwner = project.user_id.toString() === userId;
      const isCollaborator = project.collaborators && project.collaborators.some(c => c.toString() === userId);

      if (isOwner) {
        return res.json({
          projectId: project._id,
          message: "You are the project owner",
          isOwner: true
        });
      }

      if (isCollaborator) {
        return res.json({
          projectId: project._id,
          message: "Already a collaborator",
          alreadyCollaborator: true
        });
      }

      await Project.updateOne(
        { _id: project._id },
        { $addToSet: { collaborators: userId } }
      );

      console.log(`Added user ${userId} as collaborator to project ${project._id}`);

      return res.status(200).json({
        projectId: project._id,
        message: "Joined collaborative project successfully",
        isCollaborator: true
      });
    }

    if (link.permission === "edit") {
      return module.exports.copyProjectByLink(req, res);
    }

    return res.status(400).json({ error: "Invalid permission type" });

  } catch (err) {
    console.error("Error accessing shared project:", err);
    res.status(500).json({ error: err.message });
  }
};