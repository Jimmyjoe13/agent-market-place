"use client";

import React, { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Save, User, Mail, Camera, Loader2, Shield } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { api } from "@/lib/api";

const profileSchema = z.object({
  name: z.string().min(2, "Le nom doit contenir au moins 2 caractères").max(50),
  email: z.string().email("Email invalide"),
  avatar_url: z.string().url("URL invalide").optional().or(z.literal("")),
});

type ProfileFormData = z.infer<typeof profileSchema>;

export function ProfileSection() {
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  const form = useForm<ProfileFormData>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      name: "",
      email: "",
      avatar_url: "",
    },
  });

  useEffect(() => {
    async function loadProfile() {
      try {
        const profile = await api.getUserProfile();
        form.reset({
          name: profile.name || "",
          email: profile.email || "",
          avatar_url: profile.avatar_url || "",
        });
      } catch (error) {
        toast.error("Impossible de charger le profil");
      } finally {
        setIsLoading(false);
      }
    }
    loadProfile();
  }, [form]);

  async function onSubmit(values: ProfileFormData) {
    setIsSaving(true);
    try {
      await api.updateProfile({
        name: values.name,
        avatar_url: values.avatar_url,
      });
      toast.success("Profil mis à jour avec succès");
    } catch (error) {
      toast.error("Erreur lors de la mise à jour du profil");
    } finally {
      setIsSaving(false);
    }
  }

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-zinc-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-500">
      <div>
        <h3 className="text-xl font-bold tracking-tight text-zinc-100">Votre Profil</h3>
        <p className="text-sm text-zinc-400">Gérez vos informations personnelles et votre avatar.</p>
      </div>

      <div className="grid gap-6">
        <Card className="border-zinc-800 bg-zinc-900/50 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="text-sm font-medium">Informations Publiques</CardTitle>
            <CardDescription>Ces informations seront visibles par les autres membres si vous partagez vos agents.</CardDescription>
          </CardHeader>
          <CardContent>
            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                <div className="flex flex-col md:flex-row gap-6">
                  <div className="flex flex-col items-center gap-4">
                    <div className="relative group">
                      <div className="h-24 w-24 rounded-full bg-zinc-800 border-2 border-zinc-700 flex items-center justify-center overflow-hidden transition-all group-hover:border-indigo-500/50">
                        {form.watch("avatar_url") ? (
                          <img src={form.getValues("avatar_url")} alt="Avatar" className="h-full w-full object-cover" />
                        ) : (
                          <User className="h-10 w-10 text-zinc-600" />
                        )}
                        <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity cursor-pointer">
                          <Camera className="h-6 w-6 text-white" />
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="flex-1 space-y-4">
                    <FormField
                      control={form.control}
                      name="name"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Nom Complet</FormLabel>
                          <FormControl>
                            <Input {...field} className="bg-zinc-800 border-zinc-700 focus:border-indigo-500" />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="email"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Email (Non modifiable)</FormLabel>
                          <FormControl>
                            <div className="relative">
                              <Input {...field} disabled className="bg-zinc-800/50 border-zinc-700 text-zinc-500 pr-10" />
                              <Shield className="absolute right-3 top-2.5 h-4 w-4 text-zinc-600" />
                            </div>
                          </FormControl>
                          <FormDescription>Votre adresse mail principale utilisée pour la connexion.</FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="avatar_url"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>URL de l'avatar</FormLabel>
                          <FormControl>
                            <Input {...field} placeholder="https://example.com/photo.jpg" className="bg-zinc-800 border-zinc-700 focus:border-indigo-500" />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>
                </div>

                <div className="flex justify-end pt-4 border-t border-zinc-800">
                  <Button type="submit" disabled={isSaving} className="bg-indigo-600 hover:bg-indigo-500 min-w-[140px] shadow-[0_0_20px_rgba(79,70,229,0.2)]">
                    {isSaving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
                    Enregistrer
                  </Button>
                </div>
              </form>
            </Form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
