"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Share2, Trash2, Copy, Eye, Edit, Users } from "lucide-react"
import { api } from "@/lib/axios"

interface Props {
  projectId: string
  initialToken?: string | null
}

export default function ProjectShareCard({ projectId, initialToken }: Props) {
  const [token, setToken] = useState<string | null>(initialToken || null)
  const [permission, setPermission] = useState<'read' | 'edit' | 'collaborate'>('read')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (initialToken) setToken(initialToken)
  }, [initialToken])

  useEffect(() => {
    // eslint-disable-next-line no-console
    console.debug("ProjectShareCard mounted for project", projectId)
  }, [projectId])

  const createLink = async () => {
    setLoading(true)
    setError(null)
    try {
      const session = typeof window !== "undefined" ? localStorage.getItem("session") : null
      const tokenStr = session ? JSON.parse(session).token : null
      const res = await api.post(
        "/projects/share",
        { projectId, permission },
        { headers: { Authorization: `Bearer ${tokenStr}` } },
      )
      setToken(res.data.token)
    } catch (err: any) {
      setError(err?.response?.data?.error || err?.message || "Erro ao criar link")
    } finally {
      setLoading(false)
    }
  }

  const revokeLink = async () => {
    if (!token) return
    setError(null)
    try {
      const session = typeof window !== "undefined" ? localStorage.getItem("session") : null
      const tokenStr = session ? JSON.parse(session).token : null
      await api.delete(`/projects/share/${token}`, {
        headers: { Authorization: `Bearer ${tokenStr}` },
      })
      setToken(null)
    } catch (err: any) {
      setError(err?.response?.data?.error || err?.message || "Erro ao revogar link")
    }
  }

  const copyLink = () => {
    if (!token || typeof window === "undefined") return
    navigator.clipboard.writeText(`${window.location.origin}/share/${token}`)
  }

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="outline">
          <Share2 className="mr-2 h-4 w-4" />
          Partilhar
        </Button>
      </DialogTrigger>

      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Partilhar Projeto</DialogTitle>
        </DialogHeader>

        {error && (
          <div className="text-red-600 text-xs mb-2">{error}</div>
        )}

        {!token ? (
          <div className="space-y-4">
            <div className="space-y-3">
              <label className="text-sm font-medium">Tipo de Partilha</label>
              
              <div className="space-y-2">
                <button
                  type="button"
                  onClick={() => setPermission('read')}
                  className={`w-full flex items-start space-x-3 rounded-lg border p-4 text-left transition-colors ${
                    permission === 'read' 
                      ? 'border-primary bg-primary/5' 
                      : 'border-border hover:bg-accent/50'
                  }`}
                >
                  <div className={`mt-1 h-4 w-4 rounded-full border-2 flex items-center justify-center ${
                    permission === 'read' ? 'border-primary' : 'border-muted-foreground'
                  }`}>
                    {permission === 'read' && (
                      <div className="h-2 w-2 rounded-full bg-primary" />
                    )}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 font-medium">
                      <Eye className="h-4 w-4" />
                      Apenas Visualização
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      Permite visualizar e transferir as imagens processadas sem precisar de fazer login
                    </p>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => setPermission('collaborate')}
                  className={`w-full flex items-start space-x-3 rounded-lg border p-4 text-left transition-colors ${
                    permission === 'collaborate' 
                      ? 'border-primary bg-primary/5' 
                      : 'border-border hover:bg-accent/50'
                  }`}
                >
                  <div className={`mt-1 h-4 w-4 rounded-full border-2 flex items-center justify-center ${
                    permission === 'collaborate' ? 'border-primary' : 'border-muted-foreground'
                  }`}>
                    {permission === 'collaborate' && (
                      <div className="h-2 w-2 rounded-full bg-primary" />
                    )}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 font-medium">
                      <Users className="h-4 w-4" />
                      Colaboração em Tempo Real
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      Permite editar o mesmo projeto simultaneamente. Todas as alterações são visíveis em tempo real
                    </p>
                  </div>
                </button>
                
                <button
                  type="button"
                  onClick={() => setPermission('edit')}
                  className={`w-full flex items-start space-x-3 rounded-lg border p-4 text-left transition-colors ${
                    permission === 'edit' 
                      ? 'border-primary bg-primary/5' 
                      : 'border-border hover:bg-accent/50'
                  }`}
                >
                  <div className={`mt-1 h-4 w-4 rounded-full border-2 flex items-center justify-center ${
                    permission === 'edit' ? 'border-primary' : 'border-muted-foreground'
                  }`}>
                    {permission === 'edit' && (
                      <div className="h-2 w-2 rounded-full bg-primary" />
                    )}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 font-medium">
                      <Edit className="h-4 w-4" />
                      Permitir Cópia
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      Cria uma cópia independente do projeto na conta do utilizador
                    </p>
                  </div>
                </button>
              </div>
            </div>

            <Button onClick={createLink} disabled={loading} className="w-full">
              {loading ? "A criar..." : "Criar link de partilha"}
            </Button>
          </div>
        ) : (
          <div className="space-y-2">
            <Input
              readOnly
              value={`${typeof window !== "undefined" ? window.location.origin : ""}/share/${token}`}
            />
            <div className="flex gap-2">
              <Button onClick={copyLink} variant="secondary" className="flex-1">
                <Copy className="h-4 w-4 mr-1" /> Copiar
              </Button>
              <Button onClick={revokeLink} variant="destructive">
                <Trash2 className="h-4 w-4 mr-1" /> Revogar
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}