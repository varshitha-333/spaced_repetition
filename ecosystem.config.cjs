module.exports = {
  apps: [
    {
      name: 'learnflow',
      script: 'python3',
      args: 'serve.py',
      cwd: '/home/user/webapp',
      env: {
        PORT: 3000
      },
      watch: false,
      instances: 1,
      exec_mode: 'fork'
    }
  ]
}
