const express = require('express');
const cors = require('cors');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;


// 中间件
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'dist')));

// API代理到后端
app.use('/api', (req, res, next) => {
  // 这里可以添加代理逻辑，或者直接让前端通过vite代理
  next();
});

// 服务静态文件
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'dist', 'index.html'));
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`前端服务器运行在 http://0.0.0.0:${PORT}`);
});
