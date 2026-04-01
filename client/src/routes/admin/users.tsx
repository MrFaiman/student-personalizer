import { createFileRoute, redirect } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { Helmet } from "react-helmet-async";
import { useTranslation } from "react-i18next";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Users, Shield } from "lucide-react";

import { useAuthStore } from "@/lib/auth-store";
import { adminUsersApi } from "@/lib/api/admin-users";
import { authApi } from "@/lib/api/auth";
import type { SchoolOption, User, UserRole } from "@/lib/types/auth";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

export const Route = createFileRoute("/admin/users")({
  beforeLoad: () => {
    const isAdmin = useAuthStore.getState().hasRole("super_admin", "system_admin");
    if (!isAdmin) {
      throw redirect({ to: "/" });
    }
  },
  component: AdminUsersPage,
});

type ActiveFilter = "all" | "active" | "inactive";
type RoleFilter = "all" | UserRole;

function AdminUsersPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();

  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<RoleFilter>("all");
  const [activeFilter, setActiveFilter] = useState<ActiveFilter>("all");
  const [schoolFilter, setSchoolFilter] = useState<string>("__all__");

  const [createOpen, setCreateOpen] = useState(false);
  const [editUser, setEditUser] = useState<User | null>(null);
  const [resetPwUser, setResetPwUser] = useState<User | null>(null);

  const { data: schools, isLoading: schoolsLoading } = useQuery({
    queryKey: ["schools-options"],
    queryFn: authApi.schools,
  });

  const { data: users, isLoading, error } = useQuery({
    queryKey: ["admin-users"],
    queryFn: adminUsersApi.listUsers,
  });

  const filteredUsers = useMemo(() => {
    const q = search.trim().toLowerCase();
    const schoolIdFilter =
      schoolFilter === "__all__" ? null : Number(schoolFilter);

    return (users ?? [])
      .filter((u) => {
        if (!q) return true;
        return (
          u.email.toLowerCase().includes(q) ||
          u.display_name.toLowerCase().includes(q)
        );
      })
      .filter((u) => {
        if (roleFilter === "all") return true;
        return u.role === roleFilter;
      })
      .filter((u) => {
        if (activeFilter === "all") return true;
        return activeFilter === "active" ? u.is_active : !u.is_active;
      })
      .filter((u) => {
        if (schoolIdFilter == null) return true;
        return u.school_id === schoolIdFilter;
      })
      .sort((a, b) => a.email.localeCompare(b.email));
  }, [users, search, roleFilter, activeFilter, schoolFilter]);

  const createMutation = useMutation({
    mutationFn: adminUsersApi.createUser,
    onSuccess: async () => {
      setCreateOpen(false);
      await qc.invalidateQueries({ queryKey: ["admin-users"] });
    },
  });

  const updateMutation = useMutation({
    mutationFn: (args: { userId: string; patch: Parameters<typeof adminUsersApi.updateUser>[1] }) =>
      adminUsersApi.updateUser(args.userId, args.patch),
    onSuccess: async () => {
      setEditUser(null);
      await qc.invalidateQueries({ queryKey: ["admin-users"] });
    },
  });

  const resetPasswordMutation = useMutation({
    mutationFn: (args: { userId: string; new_password: string; must_change_password: boolean }) =>
      adminUsersApi.resetPassword(args.userId, {
        new_password: args.new_password,
        must_change_password: args.must_change_password,
      }),
    onSuccess: async () => {
      setResetPwUser(null);
      await qc.invalidateQueries({ queryKey: ["admin-users"] });
    },
  });

  const resetMfaMutation = useMutation({
    mutationFn: (userId: string) => adminUsersApi.resetMfa(userId),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["admin-users"] });
    },
  });

  return (
    <div className="space-y-4" dir="rtl">
      <Helmet>
        <title>{`${t("nav.userManagement")} | ${t("appName")}`}</title>
      </Helmet>

      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Users className="size-6 text-muted-foreground" />
            {t("nav.userManagement")}
          </h1>
          <p className="text-muted-foreground text-sm">
            {t("adminUsers.subtitle")}
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)} className="gap-2">
          <Shield className="size-4" />
          {t("adminUsers.create")}
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <div className="md:col-span-2">
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t("adminUsers.searchPlaceholder")}
          />
        </div>

        <Select
          value={roleFilter}
          onValueChange={(v) => setRoleFilter(v as RoleFilter)}
          dir="rtl"
        >
          <SelectTrigger>
            <SelectValue placeholder={t("adminUsers.role")} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t("general.all")}</SelectItem>
            <SelectItem value="super_admin">{t("auth.role.super_admin")}</SelectItem>
            <SelectItem value="system_admin">{t("auth.role.system_admin")}</SelectItem>
            <SelectItem value="school_admin">{t("auth.role.school_admin")}</SelectItem>
            <SelectItem value="teacher">{t("auth.role.teacher")}</SelectItem>
            <SelectItem value="read_only">{t("auth.role.read_only")}</SelectItem>
          </SelectContent>
        </Select>

        <Select
          value={activeFilter}
          onValueChange={(v) => setActiveFilter(v as ActiveFilter)}
          dir="rtl"
        >
          <SelectTrigger>
            <SelectValue placeholder={t("general.status")} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t("general.all")}</SelectItem>
            <SelectItem value="active">{t("adminUsers.active")}</SelectItem>
            <SelectItem value="inactive">{t("adminUsers.inactive")}</SelectItem>
          </SelectContent>
        </Select>

        <Select
          value={schoolFilter}
          onValueChange={(v) => setSchoolFilter(v)}
          dir="rtl"
          disabled={schoolsLoading}
        >
          <SelectTrigger className="md:col-span-2">
            <SelectValue placeholder={t("adminUsers.school")} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__all__">{t("general.all")}</SelectItem>
            {(schools ?? []).map((s) => (
              <SelectItem key={s.school_id} value={String(s.school_id)}>
                {s.school_name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {error && (
        <div className="text-sm text-destructive bg-destructive/10 rounded-md px-3 py-2">
          {(error as Error).message}
        </div>
      )}

      <Table>
        <TableHeader>
          <TableRow className="bg-accent/50">
            <TableHead className="text-right font-bold">
              {t("adminUsers.displayName")}
            </TableHead>
            <TableHead className="text-right font-bold">
              {t("adminUsers.email")}
            </TableHead>
            <TableHead className="text-right font-bold">
              {t("adminUsers.role")}
            </TableHead>
            <TableHead className="text-right font-bold">
              {t("adminUsers.school")}
            </TableHead>
            <TableHead className="text-right font-bold">
              {t("adminUsers.mfa")}
            </TableHead>
            <TableHead className="text-right font-bold">
              {t("adminUsers.identityProvider")}
            </TableHead>
            <TableHead className="text-right font-bold">
              {t("general.status")}
            </TableHead>
            <TableHead className="text-right font-bold w-[240px]">
              {t("general.actions")}
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading ? (
            <TableRow>
              <TableCell colSpan={8} className="py-12 text-center text-muted-foreground">
                {t("general.loading")}
              </TableCell>
            </TableRow>
          ) : filteredUsers.length ? (
            filteredUsers.map((u) => (
              <TableRow key={u.id} className="hover:bg-accent/30 transition-colors">
                <TableCell className="font-medium">{u.display_name}</TableCell>
                <TableCell className="font-mono text-sm">{u.email}</TableCell>
                <TableCell>{t(`auth.role.${u.role}`)}</TableCell>
                <TableCell className="max-w-[220px] truncate">
                  {u.school_name ?? "-"}
                </TableCell>
                <TableCell>
                  {u.mfa_enabled ? (
                    <Badge className="bg-green-100 text-green-700">
                      {t("adminUsers.mfaEnabled")}
                    </Badge>
                  ) : (
                    <Badge className="bg-muted text-muted-foreground">
                      {t("adminUsers.mfaDisabled")}
                    </Badge>
                  )}
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {u.identity_provider || "-"}
                </TableCell>
                <TableCell>
                  {u.is_active ? (
                    <Badge className="bg-green-100 text-green-700">
                      {t("adminUsers.active")}
                    </Badge>
                  ) : (
                    <Badge className="bg-red-100 text-red-700">
                      {t("adminUsers.inactive")}
                    </Badge>
                  )}
                </TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setEditUser(u)}
                    >
                      {t("general.edit")}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setResetPwUser(u)}
                    >
                      {t("adminUsers.resetPassword")}
                    </Button>
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button
                          variant="destructive"
                          size="sm"
                          disabled={resetMfaMutation.isPending}
                        >
                          {t("adminUsers.resetMfa")}
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>
                            {t("adminUsers.resetMfaTitle")}
                          </AlertDialogTitle>
                          <AlertDialogDescription>
                            {t("adminUsers.resetMfaDescription", {
                              email: u.email,
                            })}
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>
                            {t("general.cancel")}
                          </AlertDialogCancel>
                          <AlertDialogAction
                            variant="destructive"
                            onClick={() => resetMfaMutation.mutate(u.id)}
                          >
                            {t("general.confirm")}
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  </div>
                </TableCell>
              </TableRow>
            ))
          ) : (
            <TableRow>
              <TableCell colSpan={8} className="py-12 text-center text-muted-foreground">
                {t("adminUsers.noUsers")}
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      <CreateUserDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        schools={schools ?? []}
        onCreate={(payload) => createMutation.mutate(payload)}
        isSaving={createMutation.isPending}
        error={createMutation.error instanceof Error ? createMutation.error.message : null}
      />

      <EditUserDialog
        key={`edit-${editUser?.id ?? "none"}`}
        user={editUser}
        onClose={() => setEditUser(null)}
        schools={schools ?? []}
        onSave={(userId, patch) => updateMutation.mutate({ userId, patch })}
        isSaving={updateMutation.isPending}
        error={updateMutation.error instanceof Error ? updateMutation.error.message : null}
      />

      <ResetPasswordDialog
        key={`resetpw-${resetPwUser?.id ?? "none"}`}
        user={resetPwUser}
        onClose={() => setResetPwUser(null)}
        onReset={(userId, newPassword, mustChange) =>
          resetPasswordMutation.mutate({
            userId,
            new_password: newPassword,
            must_change_password: mustChange,
          })
        }
        isSaving={resetPasswordMutation.isPending}
        error={
          resetPasswordMutation.error instanceof Error
            ? resetPasswordMutation.error.message
            : null
        }
      />
    </div>
  );
}

function CreateUserDialog({
  open,
  onOpenChange,
  schools,
  onCreate,
  isSaving,
  error,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  schools: SchoolOption[];
  onCreate: (payload: Parameters<typeof adminUsersApi.createUser>[0]) => void;
  isSaving: boolean;
  error: string | null;
}) {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("teacher");
  const [mustChange, setMustChange] = useState(true);
  const [schoolId, setSchoolId] = useState<string>("__none__");

  const canSubmit = email.trim() && displayName.trim() && password.trim();

  function resetForm() {
    setEmail("");
    setDisplayName("");
    setPassword("");
    setRole("teacher");
    setMustChange(true);
    setSchoolId("__none__");
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        onOpenChange(v);
        if (!v) resetForm();
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("adminUsers.createTitle")}</DialogTitle>
          <DialogDescription>{t("adminUsers.createDescription")}</DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <div className="space-y-2">
            <label className="text-sm font-medium">{t("adminUsers.email")}</label>
            <Input value={email} onChange={(e) => setEmail(e.target.value)} dir="ltr" />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">{t("adminUsers.displayName")}</label>
            <Input value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">{t("adminUsers.initialPassword")}</label>
            <Input
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              type="password"
              dir="ltr"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-2">
              <label className="text-sm font-medium">{t("adminUsers.role")}</label>
              <Select value={role} onValueChange={(v) => setRole(v as UserRole)} dir="rtl">
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="super_admin">{t("auth.role.super_admin")}</SelectItem>
                  <SelectItem value="system_admin">{t("auth.role.system_admin")}</SelectItem>
                  <SelectItem value="school_admin">{t("auth.role.school_admin")}</SelectItem>
                  <SelectItem value="teacher">{t("auth.role.teacher")}</SelectItem>
                <SelectItem value="read_only">{t("auth.role.read_only")}</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">{t("adminUsers.school")}</label>
              <Select value={schoolId} onValueChange={setSchoolId} dir="rtl">
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">{t("adminUsers.noSchool")}</SelectItem>
                  {schools.map((s) => (
                    <SelectItem key={s.school_id} value={String(s.school_id)}>
                      {s.school_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              className="accent-primary"
              checked={mustChange}
              onChange={(e) => setMustChange(e.target.checked)}
            />
            {t("adminUsers.mustChangePassword")}
          </label>

          {error && (
            <div className="text-sm text-destructive bg-destructive/10 rounded-md px-3 py-2">
              {error}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {t("general.cancel")}
          </Button>
          <Button
            onClick={() =>
              onCreate({
                email,
                display_name: displayName,
                password,
                role,
                must_change_password: mustChange,
                school_id: schoolId === "__none__" ? null : Number(schoolId),
              })
            }
            disabled={!canSubmit || isSaving}
          >
            {isSaving ? t("auth.saving") : t("general.save")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function EditUserDialog({
  user,
  onClose,
  schools,
  onSave,
  isSaving,
  error,
}: {
  user: User | null;
  onClose: () => void;
  schools: SchoolOption[];
  onSave: (userId: string, patch: Parameters<typeof adminUsersApi.updateUser>[1]) => void;
  isSaving: boolean;
  error: string | null;
}) {
  const { t } = useTranslation();
  const open = !!user;

  const [displayName, setDisplayName] = useState(user?.display_name ?? "");
  const [role, setRole] = useState<UserRole>(user?.role ?? "teacher");
  const [active, setActive] = useState<boolean>(user?.is_active ?? true);
  const [schoolId, setSchoolId] = useState<string>(
    user?.school_id != null ? String(user.school_id) : "__none__",
  );

  const canSubmit = displayName.trim().length > 0;

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        if (!v) onClose();
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("adminUsers.editTitle")}</DialogTitle>
          <DialogDescription>
            {user ? t("adminUsers.editDescription", { email: user.email }) : ""}
          </DialogDescription>
        </DialogHeader>

        {user && (
          <div className="space-y-3">
            <div className="space-y-2">
              <label className="text-sm font-medium">{t("adminUsers.displayName")}</label>
              <Input value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="space-y-2">
                <label className="text-sm font-medium">{t("adminUsers.role")}</label>
                <Select value={role} onValueChange={(v) => setRole(v as UserRole)} dir="rtl">
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="super_admin">{t("auth.role.super_admin")}</SelectItem>
                    <SelectItem value="system_admin">{t("auth.role.system_admin")}</SelectItem>
                    <SelectItem value="school_admin">{t("auth.role.school_admin")}</SelectItem>
                    <SelectItem value="teacher">{t("auth.role.teacher")}</SelectItem>
                    <SelectItem value="read_only">{t("auth.role.read_only")}</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">{t("general.status")}</label>
                <Select
                  value={active ? "active" : "inactive"}
                  onValueChange={(v) => setActive(v === "active")}
                  dir="rtl"
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="active">{t("adminUsers.active")}</SelectItem>
                    <SelectItem value="inactive">{t("adminUsers.inactive")}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">{t("adminUsers.school")}</label>
              <Select value={schoolId} onValueChange={setSchoolId} dir="rtl">
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">{t("adminUsers.noSchool")}</SelectItem>
                  {schools.map((s) => (
                    <SelectItem key={s.school_id} value={String(s.school_id)}>
                      {s.school_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {error && (
              <div className="text-sm text-destructive bg-destructive/10 rounded-md px-3 py-2">
                {error}
              </div>
            )}
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            {t("general.cancel")}
          </Button>
          <Button
            onClick={() => {
              if (!user) return;
              onSave(user.id, {
                display_name: displayName,
                role,
                is_active: active,
                school_id: schoolId === "__none__" ? null : Number(schoolId),
              });
            }}
            disabled={!user || !canSubmit || isSaving}
          >
            {isSaving ? t("auth.saving") : t("general.save")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function ResetPasswordDialog({
  user,
  onClose,
  onReset,
  isSaving,
  error,
}: {
  user: User | null;
  onClose: () => void;
  onReset: (userId: string, newPassword: string, mustChange: boolean) => void;
  isSaving: boolean;
  error: string | null;
}) {
  const { t } = useTranslation();
  const open = !!user;
  const [newPassword, setNewPassword] = useState("");
  const [mustChange, setMustChange] = useState(true);

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        if (!v) {
          setNewPassword("");
          setMustChange(true);
          onClose();
        }
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("adminUsers.resetPasswordTitle")}</DialogTitle>
          <DialogDescription>
            {user ? t("adminUsers.resetPasswordDescription", { email: user.email }) : ""}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <div className="space-y-2">
            <label className="text-sm font-medium">{t("adminUsers.newPassword")}</label>
            <Input
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              type="password"
              dir="ltr"
            />
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              className="accent-primary"
              checked={mustChange}
              onChange={(e) => setMustChange(e.target.checked)}
            />
            {t("adminUsers.mustChangePassword")}
          </label>

          {error && (
            <div className="text-sm text-destructive bg-destructive/10 rounded-md px-3 py-2">
              {error}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            {t("general.cancel")}
          </Button>
          <Button
            onClick={() => {
              if (!user) return;
              onReset(user.id, newPassword, mustChange);
            }}
            disabled={!user || newPassword.trim().length === 0 || isSaving}
          >
            {isSaving ? t("auth.saving") : t("general.confirm")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

