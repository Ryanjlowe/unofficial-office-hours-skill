
const stream = require('stream');
const youtubedl = require('youtube-dl');
const AWS = require('aws-sdk');


const bucket = process.env.BUCKET_NAME;

exports.handler = async (event) => {

  console.log(event);

  const key = "unprocessed/" + event.youtubeVideName + ".mp4";
  const passtrough = new stream.PassThrough();

  const dl = youtubedl(event.youtubeUrl, ['--format=best[ext=mp4]'], {maxBuffer: Infinity});
  dl.pipe(passtrough); // write video to the pass-through stream


  const p = new Promise();

  const upload = new AWS.S3.ManagedUpload({
    params: {
      Bucket: bucket,
      Key: key,
      Body: passtrough
    },
    partSize: 1024 * 1024 * 64 // 64 MB in bytes
  });
  upload.send((err) => {
    if (err) {
      console.log('error', err);
    } else {
      console.log('done');

      p.resolve( {
        "mediaS3Location": {
          "bucket": bucket,
          "key": key
        }
      });
    }
  });

  return p;
};
