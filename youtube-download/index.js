const stream = require('stream');
const AWS = require('aws-sdk');

const fs = require('fs');
const ytdl = require('ytdl-core');

const bucket = process.env.BUCKET_NAME;

exports.handler = async (event) => {

  console.log(event);
  const passthrough = new stream.PassThrough();

  var info = await ytdl.getInfo(event.youtubeUrl);
  var name = info.player_response.videoDetails.title.replace(/[^a-zA-Z0-9]+/g, "-");

  const key = `unprocessed/${name}.mp4`;

  ytdl(event.youtubeUrl)
    .pipe(passthrough);

  const p = new Promise((resolve, reject) => {

    const upload = new AWS.S3.ManagedUpload({
      params: {
        Bucket: bucket,
        Key: key,
        Body: passthrough
      },
      partSize: 1024 * 1024 * 64 // 64 MB in bytes
    });
    upload.send((err) => {
      if (err) {
        console.log('error', err);
        reject(err);
      } else {
        console.log('done');

       resolve( {
          "mediaS3Location": {
            "bucket": bucket,
            "key": key
          }
        });
      }
    });
  })

  return p;
};
