const jwt = require("jsonwebtoken");

module.exports.checkToken = (req, res, next) => {
  const token = req.headers["authorization"]?.split(" ")[1];

  if (!token) {
    res.status(401).jsonp(`Please provide a JWT token`);
    return;
  }

  jwt.verify(token, process.env.JWT_SECRET_KEY, (e, payload) => {
    if (e) {
      res.status(401).jsonp(`Invalid JWT signature or token expired.`);
      return;
    }

    try {
      const user = payload;
      const user_id = user.id;
      const exp = user.exp;

      if (Date.now() >= exp * 1000) {
        res.status(401).jsonp(`JWT expired.`);
        return;
      }

      // Only enforce user match if req.params.user is present
      if (req.params.user && user_id !== req.params.user) {
        res.status(401).jsonp(`Request's user and JWT's user don't match`);
        return;
      }

      req.user = user;
      next();
    } catch (_) {
      res.status(401).jsonp(`Invalid JWT`);
    }
  });
};
