'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { api } from '@/lib/axios'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useSession } from '@/providers/session-provider'
import { Download, Copy, Users } from 'lucide-react'

interface ProjectImage {
  _id: string
  name: string
  url: string
}

interface SharedProject {
  _id: string
  name: string
  imgs: any[]
  tools: any[]
  description?: string
}

interface ShareData {
  project: SharedProject
  permission: 'read' | 'edit' | 'collaborate'
  images?: ProjectImage[]
}

export default function SharedProjectPage() {
  const { token } = useParams()
  const router = useRouter()
  const session = useSession()
  const [shareData, setShareData] = useState<ShareData | null>(null)
  const [images, setImages] = useState<ProjectImage[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingImages, setLoadingImages] = useState(false)
  const [downloadingImage, setDownloadingImage] = useState<string | null>(null)
  const [accessing, setAccessing] = useState(false)
  
  useEffect(() => {
    if (!token) return

    api.get(`/projects/share/${token}`)
      .then(res => {
        setShareData(res.data)
        setLoading(false)
        
        // If read-only, load images for preview
        if (res.data.permission === 'read') {
          loadProjectImages(res.data.project)
        }
      })
      .catch(() => {
        setError('Link inválido ou expirado')
        setLoading(false)
      })
  }, [token])

  const loadProjectImages = async (project: SharedProject) => {
    setLoadingImages(true)
    try {
      const imagePromises = project.imgs.map(async (img) => {
        try {
          const response = await api.get(
            `/projects/share/${token}/image/${img._id}`
          )
          return response.data
        } catch (err) {
          console.error(`Error loading image ${img._id}:`, err)
          return null
        }
      })

      const loadedImages = (await Promise.all(imagePromises)).filter(Boolean)
      setImages(loadedImages)
    } catch (err) {
      console.error('Error loading images:', err)
    } finally {
      setLoadingImages(false)
    }
  }

  const downloadImage = async (image: ProjectImage) => {
    setDownloadingImage(image._id)
    try {
      const response = await fetch(image.url)
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = image.name
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (err) {
      console.error('Error downloading image:', err)
    } finally {
      setDownloadingImage(null)
    }
  }

  const handleAccessProject = async () => {
    if (!session?.token) {
      localStorage.setItem('redirectAfterLogin', `/share/${token}`)
      router.push('/login')
      return
    }

    setAccessing(true)
    try {
      const result = await api.post(
        `/projects/share/${token}/access`,
        {},
        {
          headers: {
            Authorization: `Bearer ${session.token}`
          }
        }
      )
      
      
      router.push(`/dashboard/${result.data.projectId}`)
    } catch (err: any) {
      setError(err?.response?.data?.error || 'Erro ao aceder ao projeto. Tente novamente.')
      setAccessing(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-muted-foreground">A carregar projeto...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="w-full max-w-md">
          <CardContent className="pt-6">
            <p className="text-center text-red-500">{error}</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (!shareData) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-muted-foreground">Projeto não encontrado</p>
      </div>
    )
  }

  const { project, permission } = shareData
  const isReadOnly = permission === 'read'
  const isCollaborative = permission === 'collaborate'

  // Read-only view - clean and focused on images
  if (isReadOnly) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-background to-muted/20">
        <div className="container max-w-7xl mx-auto px-4 py-12">
          {/* Header */}
          <div className="text-center mb-12">
            <h1 className="text-4xl font-bold mb-2">{project.name}</h1>
            {project.description && (
              <p className="text-muted-foreground text-lg">{project.description}</p>
            )}
            <p className="text-sm text-muted-foreground mt-4">
              {images.length} {images.length === 1 ? 'imagem' : 'imagens'}
            </p>
          </div>

          {/* Images Grid */}
          {loadingImages ? (
            <div className="text-center py-16">
              <p className="text-muted-foreground">A carregar imagens...</p>
            </div>
          ) : images.length === 0 ? (
            <div className="text-center py-16">
              <p className="text-muted-foreground">Nenhuma imagem disponível</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {images.map((img) => (
                <Card key={img._id} className="overflow-hidden group hover:shadow-lg transition-shadow">
                  <div className="relative aspect-square bg-muted">
                    <img
                      src={img.url}
                      alt={img.name}
                      className="object-cover w-full h-full"
                    />
                  </div>
                  <CardContent className="p-4">
                    <p className="text-sm font-medium truncate mb-3"></p>
                    <Button
                      size="sm"
                      variant="outline"
                      className="w-full"
                      onClick={() => downloadImage(img)}
                      disabled={downloadingImage === img._id}
                    >
                      <Download className="h-4 w-4 mr-2" />
                      {downloadingImage === img._id ? 'A transferir...' : 'Transferir'}
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    )
  }

  // Editable/Collaborative view
  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <Card className="w-full max-w-2xl">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-2xl">{project.name}</CardTitle>
            <Badge variant={isCollaborative ? 'default' : 'secondary'}>
              {isCollaborative ? (
                <><Users className="h-3 w-3 mr-1" /> Colaborativo</>
              ) : (
                <><Copy className="h-3 w-3 mr-1" /> Copiar</>
              )}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <p className="text-muted-foreground">
            {project.description || 'Sem descrição'}
          </p>
          
          <div className="grid grid-cols-2 gap-4 py-4">
            <div className="text-center p-4 bg-muted/50 rounded-lg">
              <p className="text-2xl font-bold">{project.imgs?.length || 0}</p>
              <p className="text-sm text-muted-foreground">Imagens</p>
            </div>
            <div className="text-center p-4 bg-muted/50 rounded-lg">
              <p className="text-2xl font-bold">{project.tools?.length || 0}</p>
              <p className="text-sm text-muted-foreground">Ferramentas</p>
            </div>
          </div>

          {isCollaborative && (
            <div className="bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
              <div className="flex gap-2">
                <Users className="h-5 w-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-medium text-blue-900 dark:text-blue-100">Projeto Colaborativo</h3>
                  <p className="text-sm text-blue-700 dark:text-blue-300 mt-1">
                    Vai trabalhar no mesmo projeto com o proprietário. Todas as alterações serão visíveis em tempo real.
                  </p>
                </div>
              </div>
            </div>
          )}

          {!isCollaborative && (
            <div className="bg-muted/50 rounded-lg p-4">
              <div className="flex gap-2">
                <Copy className="h-5 w-5 text-muted-foreground flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-medium">Cópia do Projeto</h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    Será criada uma cópia deste projeto na sua conta que pode editar livremente.
                  </p>
                </div>
              </div>
            </div>
          )}

          <div className="pt-4">
            <Button 
              onClick={handleAccessProject}
              disabled={accessing}
              className="w-full"
              size="lg"
            >
              {isCollaborative ? (
                <><Users className="h-4 w-4 mr-2" /> {accessing ? 'A aceder...' : 'Colaborar neste Projeto'}</>
              ) : (
                <><Copy className="h-4 w-4 mr-2" /> {accessing ? 'A copiar...' : 'Copiar para a minha conta'}</>
              )}
            </Button>
            
            {!session?.token && (
              <p className="text-xs text-muted-foreground text-center mt-3">
                Será redirecionado para fazer login
              </p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}