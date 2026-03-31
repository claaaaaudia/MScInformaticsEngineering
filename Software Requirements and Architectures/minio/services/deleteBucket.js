const s3 = require("./s3ClientDocker"); // minio s3 client

async function deleteBucket(bucketName) {
  try {

    const listParams = { // list all buckets
      Bucket: bucketName,
    };

    // pagination helpers, probably not necessary but anyway...
    let continuationToken = null;
    let hasMore = true;

    while (hasMore) { // delete the objects in the bucket
      const listParams = {
        Bucket: bucketName,
      };

      if (continuationToken) {
        listParams.ContinuationToken = continuationToken;
      }

      // get the files from the s3 storage
      const listResponse = await s3.listObjectsV2(listParams).promise();

      if (listResponse.Contents && listResponse.Contents.length > 0) {
        const deleteParams = {
          Bucket: bucketName,
          Delete: {
            Objects: listResponse.Contents.map((obj) => ({
              Key: obj.Key,
            })),
          },
        };

        // send deletion command
        await s3.deleteObjects(deleteParams).promise();
      }

      hasMore = listResponse.IsTruncated;
      continuationToken = listResponse.NextContinuationToken;
    }

    // delete the bucket itself
    await s3.deleteBucket({ Bucket: bucketName }).promise();
    console.log(`Bucket '${bucketName}' deleted!`);
    return { message: `Bucket '${bucketName}' deleted!` };
  } catch (error) {
    console.error("Error deleting bucket:", error.message);
    throw error;
  }
}

module.exports = deleteBucket;
