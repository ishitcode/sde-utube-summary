const mongoose = require('mongoose');

async function connectDB() {
  const mongoUri = process.env.MONGO_URI || 'mongodb://127.0.0.1:27017/youtube-summary-studio';

  try {
    await mongoose.connect(mongoUri);
    console.log('MongoDB connected');
  } catch (error) {
    console.warn('MongoDB connection failed. Continuing without database for local onboarding.', error.message);
  }
}

module.exports = { connectDB };
