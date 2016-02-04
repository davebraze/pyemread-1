a=dir('195*');
curDir = pwd;
path(path, curDir)
 
for i = 1:length(a)
   cd(a(i).name)

   
   b=dir('*.TextGrid');

   
   for j = 1:length(b)
       makeXLS(b(j).name);
   end
   cd ..
end