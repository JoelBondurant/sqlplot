drop table if exists connection;

create table if not exists connection (
	id serial primary key,
	xconnection_id varchar(32) not null,
	"type" varchar(16) not null,
	name varchar(32) not null,
	configuration text not null
);
