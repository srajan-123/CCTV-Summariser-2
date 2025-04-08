"use client"

import { useState, useRef, useEffect } from "react"
import { Header } from "@/components/header"
// Footer removed
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Upload,
  Play,
  Pause,
  SkipForward,
  Download,
  Film,
  Clock,
  Zap,
  ChevronRight,
} from "lucide-react"

export default function Home() {
  const [videoFile, setVideoFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [processingStage, setProcessingStage] = useState(0)
  const [processSteps, setProcessSteps] = useState<string[]>([]) // Simulated processing steps
  const [detectionLogs, setDetectionLogs] = useState<string[]>([]) // Actual logs from backend detection
  const [videoReady, setVideoReady] = useState(false) // Flag indicating processed video is ready
  const [videoURL, setVideoURL] = useState("")
  const [activeTab, setActiveTab] = useState("upload")
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  // videoRef removed as we are not displaying video

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file && file.type.startsWith("video/")) {
      setVideoFile(file)
      setProcessSteps([])
      setDetectionLogs([])
      setVideoURL("")
      setVideoReady(false)
      setActiveTab("upload")
    }
  }

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = () => {
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file && file.type.startsWith("video/")) {
      setVideoFile(file)
      setProcessSteps([])
      setDetectionLogs([])
      setVideoURL("")
      setVideoReady(false)
      setActiveTab("upload")
    }
  }

  const handleUpload = async () => {
    if (!videoFile) return

    setLoading(true)
    setProcessSteps([])
    setDetectionLogs([])
    setVideoURL("")
    setProcessingStage(0)
    setVideoReady(false)

    const formData = new FormData()
    formData.append("file", videoFile)

    try {
      // Simulate realistic processing stages and update process steps
      const stageMessages = [
        "Initializing CCTV footage processing...",
        "Analyzing footage for motion...",
        "Detecting objects of interest...",
        "Optimizing video segments...",
        "Generating optimized output...",
      ]
      for (let i = 0; i < stageMessages.length; i++) {
        setProcessSteps((prev) => [...prev, stageMessages[i]])
        await simulateProcessingStage(i + 1)
      }

      // Call backend API to process video
      const res = await fetch("http://localhost:8000/process-video", {
        method: "POST",
        body: formData,
      })
      const data = await res.json()
      // data.logs contains detection logs (timestamps and detected objects)
      setDetectionLogs(data.logs)
      setProcessSteps((prev) => [...prev, "Processing complete!"])

      // Request summary video from backend using the provided file path
      const videoRes = await fetch(
        `http://localhost:8000/download-video?video_path=${encodeURIComponent(data.summary_video)}`
      )
      if (videoRes.ok) {
        const blob = await videoRes.blob()
        setVideoURL(URL.createObjectURL(blob))
        setVideoReady(true)
        // Alert the user that the video is ready and switch to the Results tab
        alert("Video processing complete! Please check the Results tab to view download options and logs.")
        setActiveTab("results")
      }
    } catch (error) {
      console.error("Error:", error)
      setProcessSteps((prev) => [...prev, "Error processing video. Please try again."])
    }
    setLoading(false)
  }

  const simulateProcessingStage = async (stage: number) => {
    return new Promise((resolve) => {
      setTimeout(() => {
        setProcessingStage(stage)
        resolve(true)
      }, 1500)
    })
  }

  const downloadVideo = () => {
    if (videoURL) {
      const a = document.createElement("a")
      a.href = videoURL
      a.download = "cctv_optimized_video.mp4"
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
    }
  }

  return (
    <main className="min-h-screen flex flex-col bg-background">
      <Header />

      <section className="flex-1 pt-24 pb-16">
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto">
            <div className="text-center mb-12">
              <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight mb-4 bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-cyan-400">
                CCTV Footage Optimizer
              </h1>
              <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
                Enhance your surveillance footage with advanced AI-driven activity detection and optimization.
              </p>
            </div>

            <Card className="border border-blue-900/30 shadow-lg shadow-blue-500/5 bg-card">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Film className="h-5 w-5 text-blue-400" />
                  Video Processing
                </CardTitle>
                <CardDescription>Upload your CCTV footage to optimize recording segments</CardDescription>
              </CardHeader>
              <CardContent>
                <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                  <TabsList className="grid w-full grid-cols-2 mb-6 bg-muted">
                    <TabsTrigger value="upload">Upload Video</TabsTrigger>
                    <TabsTrigger value="results" disabled={!videoReady && detectionLogs.length === 0}>
                      Results
                    </TabsTrigger>
                  </TabsList>

                  <TabsContent value="upload" className="space-y-6">
                    <div
                      className={`file-drop-area rounded-xl border-2 border-dashed p-8 text-center transition-all ${isDragging ? "border-blue-500 bg-blue-500/10" : "border-blue-900/30"} ${videoFile ? "bg-blue-500/5" : ""}`}
                      onDragOver={handleDragOver}
                      onDragLeave={handleDragLeave}
                      onDrop={handleDrop}
                      onClick={() => fileInputRef.current?.click()}
                    >
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept="video/*"
                        onChange={handleFileChange}
                        className="hidden"
                      />
                      <div className="flex flex-col items-center justify-center gap-4">
                        <div className="rounded-full bg-blue-500/20 p-4">
                          <Upload className="h-8 w-8 text-blue-400" />
                        </div>
                        {videoFile ? (
                          <div>
                            <p className="font-medium">{videoFile.name}</p>
                            <p className="text-sm text-muted-foreground">
                              {(videoFile.size / (1024 * 1024)).toFixed(2)} MB
                            </p>
                          </div>
                        ) : (
                          <div>
                            <p className="font-medium">Drag and drop your CCTV video file here</p>
                            <p className="text-sm text-muted-foreground">or click to browse your files</p>
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="flex justify-center">
                      <Button
                        size="lg"
                        onClick={handleUpload}
                        disabled={!videoFile || loading}
                        className="relative overflow-hidden group bg-blue-600 hover:bg-blue-700"
                      >
                        {loading ? (
                          <span className="flex items-center gap-2">
                            <span className="h-4 w-4 rounded-full border-2 border-current border-r-transparent animate-spin" />
                            Processing...
                          </span>
                        ) : (
                          <span className="flex items-center gap-2">
                            <Zap className="h-4 w-4" />
                            Optimize Video
                          </span>
                        )}
                        <span className="absolute inset-0 translate-y-full bg-blue-500/20 transition-transform group-hover:translate-y-0"></span>
                      </Button>
                    </div>

                    {loading && (
                      <div className="space-y-4 mt-8 p-4 rounded-lg border border-blue-900/30 bg-secondary/50">
                        <div className="flex items-center justify-between">
                          <h3 className="font-medium">Processing CCTV Footage</h3>
                          <span className="text-sm text-muted-foreground">Stage {processingStage} of 5</span>
                        </div>
                        <div className="space-y-2 max-h-40 overflow-y-auto">
                          {processSteps.map((step, index) => (
                            <div key={index} className="log-item text-sm p-2 rounded bg-secondary flex items-center gap-2">
                              <ChevronRight className="h-4 w-4 mt-0.5 text-blue-400" />
                              <span>{step}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </TabsContent>

                  <TabsContent value="results">
                    {videoReady ? (
                      <div className="space-y-6">
                        <div className="text-center p-4 rounded">
                          <p className="text-white text-lg mb-2">Your optimized video is ready!</p>
                          <Button onClick={downloadVideo} className="bg-blue-600 hover:bg-blue-700 text-white">
                            <Download className="h-5 w-5 mr-2" />
                            Download Video
                          </Button>
                        </div>
                        <div className="mt-6">
                          <h3 className="text-xl font-bold mb-4">Detection Logs</h3>
                          <div className="space-y-2 max-h-64 overflow-y-auto">
                            {detectionLogs.length > 0 ? (
                              detectionLogs.map((log, index) => (
                                <div key={index} className="log-item text-sm p-2 rounded  flex items-center gap-2">
                                  <ChevronRight className="h-4 w-4 mt-0.5 text-blue-400" />
                                  <span>{log}</span>
                                </div>
                              ))
                            ) : (
                              <p className="text-sm text-muted-foreground">No detection logs available.</p>
                            )}
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="text-center">
                        <p className="text-lg font-medium">Optimized video processing complete.</p>
                        <p className="text-sm text-muted-foreground">Please switch to the Results tab to download and view detection logs.</p>
                      </div>
                    )}
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>


    </main>
  )
}
