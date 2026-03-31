var Project = require("../models/project");
const ShareLink = require("../models/shareLink");

module.exports.getAll = async (user_id) => {
  return await Project.find({ user_id: user_id }).sort({ _id: 1 }).exec();
};

module.exports.getAllAccessible = async (user_id) => {
  return await Project.find({
    $or: [
      { user_id: user_id },
      { collaborators: user_id }
    ]
  }).sort({ _id: 1 }).exec();
};

module.exports.getOne = async (user_id, project_id) => {
  return await Project.findOne({ user_id: user_id, _id: project_id }).exec();
};

module.exports.getOneWithAccess = async (user_id, project_id) => {
  return await Project.findOne({
    _id: project_id,
    $or: [
      { user_id: user_id },
      { collaborators: user_id }
    ]
  }).exec();
};

module.exports.canAccess = async (user_id, project_id) => {
  const project = await Project.findById(project_id);
  if (!project) return false;
  return project.user_id.toString() === user_id.toString() || 
         project.collaborators.some(c => c.toString() === user_id.toString());
};

module.exports.getOneByToken = async (token) => {
  const link = await ShareLink.findOne({ token, revoked: false });
  if (!link) return null;
  return await Project.findById(link.project_id);
};

module.exports.getPermissionByToken = async (token) => {
  const link = await ShareLink.findOne({ token, revoked: false });
  if (!link) return null;
  return link.permission;
};

module.exports.create = async (project) => {
  return await Project.create(project);
};

module.exports.update = (user_id, project_id, project) => {
  return Project.updateOne({ user_id: user_id, _id: project_id }, project);
};

module.exports.updateWithAccess = async (user_id, project_id, project) => {
  const canEdit = await module.exports.canAccess(user_id, project_id);
  if (!canEdit) return null;
  return Project.updateOne({ _id: project_id }, project);
};

module.exports.updateByToken = async (token, project) => {
  const link = await ShareLink.findOne({ token, revoked: false });
  if (!link || (link.permission !== "edit" && link.permission !== "collaborate")) return null;
  return await Project.updateOne({ _id: link.project_id }, project);
};

module.exports.delete = (user_id, project_id) => {
  return Project.deleteOne({ user_id: user_id, _id: project_id });
};

module.exports.addCollaborator = async (project_id, user_id) => {
  return await Project.updateOne(
    { _id: project_id },
    { $addToSet: { collaborators: user_id } } // $addToSet prevents duplicates
  );
};

module.exports.removeCollaborator = async (project_id, user_id) => {
  return await Project.updateOne(
    { _id: project_id },
    { $pull: { collaborators: user_id } }
  );
};