// Simple Tailwind Test Component
import React from 'react'

const TailwindTest = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
      <div className="bg-white p-8 rounded-xl shadow-2xl max-w-md">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          Tailwind CSS Test
        </h1>
        <p className="text-gray-600 mb-6">
          If you can see this styled correctly, Tailwind is working!
        </p>
        <button className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
          Test Button
        </button>
        <div className="mt-6 grid grid-cols-3 gap-2">
          <div className="h-16 bg-red-500 rounded"></div>
          <div className="h-16 bg-green-500 rounded"></div>
          <div className="h-16 bg-blue-500 rounded"></div>
        </div>
      </div>
    </div>
  )
}

export default TailwindTest
