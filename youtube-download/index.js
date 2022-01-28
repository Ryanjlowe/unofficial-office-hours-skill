const stream = require('stream');
const AWS = require('aws-sdk');

const fs = require('fs');
const ytdl = require('ytdl-core');

const bucket = process.env.BUCKET_NAME;
const table_name = process.env.TABLE_NAME;

var docClient = new AWS.DynamoDB.DocumentClient();

exports.handler = async (event) => {

  console.log(event);
  const passthrough = new stream.PassThrough();

  const info = await ytdl.getInfo(event.youtubeUrl);
  const title = info.videoDetails.title;
  const name = title.replace(/[^a-zA-Z0-9]+/g, "-");
  const publishDate = info.videoDetails.publishDate;
  const id = info.videoDetails.videoId;
  const description = info.videoDetails.description;
  const lengthSeconds = info.videoDetails.lengthSeconds;

  // Example to ensure the format is available
  // let format = ytdl.chooseFormat(info.formats, { quality: '137' });

  const key = `unprocessed/${name}.mp4`;

  var params = {
      TableName: table_name,
      Item: {
          "id":  id,
          "title": title,
          "name": name,
          "key": key,
          "publishDate": publishDate,
          "description": description,
          "lengthSeconds": lengthSeconds
      }
  };

  return docClient.put(params).promise()
    .then(() => {

      ytdl(event.youtubeUrl, { quality: '22' })
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
    })
    .catch((error) => {
      console.error(error);
      return {};
    })
};
